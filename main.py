import argparse
from pathlib import Path
import os

from langchain_ollama import ChatOllama

from src import LLMAgent, JobSchemaParser, build_selection_schema, SkillsResult, build_profile, render_cv
from src.render import TEMPLATE_DIR

PROMPT_FOLDER = os.path.abspath(os.path.join("src", "prompts"))

SKILL_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "skills_system.md")
SKILL_HUMAN_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "skills_human.md")

ACTIVITY_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "activity_system.md")
ACTIVITY_HUMAN_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "activity_human.md")

REWRITE_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "rewrite_system.md")
REWRITE_HUMAN_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "rewrite_human.md")

ABOUT_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "about_system.md")
ABOUT_HUMAN_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "about_human.md")

DEFAULT_TEMPLATE = "cv.tex.j2"
DEFAULT_OUT_DIR = str(TEMPLATE_DIR.parent / "build")


def main():
    parser = argparse.ArgumentParser(
        prog="AutoCV",
        description="Generate CV from candidate profile based on job offer")
    parser.add_argument("filename", help="Path to the candidate profile file")
    parser.add_argument("job_offer", help="Path to the job offer .txt file")
    parser.add_argument("--out-dir", type=str, default=DEFAULT_OUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--template", type=str, default=DEFAULT_TEMPLATE,
                        help=f"Jinja template name (default: {DEFAULT_TEMPLATE})")
    args = parser.parse_args()

    with open(args.filename, "r", encoding="utf-8") as file:
        biography = file.read()

    with open(args.job_offer, "r", encoding="utf-8") as file:
        job_offer = file.read()

    llm = ChatOllama(
        model="qwen2.5:3b-instruct",  # qwen3:30b-a3b
        temperature=0,
        num_ctx=8192
    )

    skill_extractor = LLMAgent(
        llm=llm,
        system_prompt_path=SKILL_SYSTEM_PROMPT_PATH,
        human_prompt_path=SKILL_HUMAN_PROMPT_PATH,
    )

    skills_result = skill_extractor.invoke_with_schema(
        SkillsResult, profile=biography, job=job_offer)

    activity_picker = LLMAgent(
        llm=llm,
        system_prompt_path=ACTIVITY_SYSTEM_PROMPT_PATH,
        human_prompt_path=ACTIVITY_HUMAN_PROMPT_PATH,
    )

    job_schema_parser = JobSchemaParser(args.filename)
    parsed_profile = job_schema_parser.parse()

    work_ids = list(parsed_profile["Work_experience"].keys())
    act_ids = list(parsed_profile["Activities"].keys())
    edu_ids = list(parsed_profile["Education"].keys())
    proj_ids = list(parsed_profile["Projects"].keys())

    Selection = build_selection_schema(work_ids, act_ids, edu_ids, proj_ids)

    activity_result = activity_picker.invoke_with_schema(
        Selection, profile=biography, job=job_offer)

    choosen_work = activity_result.work
    choosen_activities = activity_result.activities
    choosen_education = activity_result.education
    choosen_projects = activity_result.projects

    ghost_writer = LLMAgent(
        llm=llm,
        system_prompt_path=REWRITE_SYSTEM_PROMPT_PATH,
        human_prompt_path=REWRITE_HUMAN_PROMPT_PATH,
    )

    work_descriptions = {}
    activity_descriptions = {}
    project_descriptions = {}
    selected_facts = ""

    for work in choosen_work:
        work_descriptions[work] = ghost_writer.invoke(
            block=parsed_profile["Work_experience"][work]["description"], job=job_offer).content
        selected_facts += f"{work} ({parsed_profile['Work_experience'][work]['company']}): {work_descriptions[work]}\n\n"
    for activity in choosen_activities:
        activity_descriptions[activity] = ghost_writer.invoke(
            block=parsed_profile["Activities"][activity]["description"], job=job_offer).content
        selected_facts += f"{activity} ({parsed_profile['Activities'][activity]['organization']}): {activity_descriptions[activity]}\n\n"
    for project in choosen_projects:
        project_descriptions[project] = ghost_writer.invoke(
            block=parsed_profile["Projects"][project]["description"], job=job_offer).content
        selected_facts += f"{project} ({parsed_profile['Projects'][project]['name']}): {project_descriptions[project]}\n\n"

    about_agent = LLMAgent(
        llm=llm,
        system_prompt_path=ABOUT_SYSTEM_PROMPT_PATH,
        human_prompt_path=ABOUT_HUMAN_PROMPT_PATH
    )

    about = about_agent.invoke(
        job=job_offer, base_about=parsed_profile["About"], selected_facts=selected_facts, selected_skills=skills_result.categories)

    profile = build_profile(about=about.content,
                            education=choosen_education,
                            work_experience=work_descriptions,
                            projects=project_descriptions,
                            activities=activity_descriptions,
                            skills=skills_result,
                            job_schema_parser_result=parsed_profile)

    render_cv(profile, out_dir=Path(args.out_dir), template=args.template)


if __name__ == "__main__":
    main()
