import argparse
import os
import logging
from pathlib import Path

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

from src import LLMAgent, JobSchemaParser, build_selection_schema, SkillsResult, build_profile, render_cv
from src.render import TEMPLATE_DIR

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

    logger.info("Creating llm")
    # llm = ChatGoogleGenerativeAI(
    #    # "gemini-2.5-flash-lite",  # "gemma-4-31b-it",  # "gemma-4-26b-a4b-it"
    #    model="gemini-3.1-flash-lite",
    #    temperature=0,
    # )
    llm = ChatOllama(
        model="qwen2.5:3b-instruct",  # qwen3:30b-a3b
        temperature=0,
        num_ctx=8192
    )

    logger.info("Creating skill extractor agent")
    skill_extractor = LLMAgent(
        llm=llm,
        system_prompt_path=SKILL_SYSTEM_PROMPT_PATH,
        human_prompt_path=SKILL_HUMAN_PROMPT_PATH,
    )

    logger.info("Retrieving skills information")
    skills_result = skill_extractor.invoke_with_schema(
        SkillsResult, profile=biography, job=job_offer)
    logger.info(f"Skill explanation: {skills_result.explanation}")

    logger.info("Creating skill activity picker agent")
    activity_picker = LLMAgent(
        llm=llm,
        system_prompt_path=ACTIVITY_SYSTEM_PROMPT_PATH,
        human_prompt_path=ACTIVITY_HUMAN_PROMPT_PATH,
    )

    logger.info("Creating schema parser")
    job_schema_parser = JobSchemaParser(args.filename)
    parsed_profile = job_schema_parser.parse()

    work_ids = list(parsed_profile["Work_experience"].keys())
    act_ids = list(parsed_profile["Activities"].keys())
    edu_ids = list(parsed_profile["Education"].keys())
    proj_ids = list(parsed_profile["Projects"].keys())

    logger.info("Building selection schema for picker")
    Selection = build_selection_schema(work_ids, act_ids, edu_ids, proj_ids)

    logger.info("Choosing important skills")
    activity_result = activity_picker.invoke_with_schema(
        Selection, profile=biography, job=job_offer)

    logger.info(f"Work reasoning: {activity_result.work_reasoning}")
    choosen_work = activity_result.work
    logger.info(
        f"Activities reasoning: {activity_result.activities_reasoning}")
    choosen_activities = activity_result.activities
    logger.info(f"Education reasoning: {activity_result.education_reasoning}")
    choosen_education = activity_result.education
    logger.info(f"Projects reasoning: {activity_result.projects_reasoning}")
    choosen_projects = activity_result.projects

    logger.info("Creating agent for summarizing activities and projects")
    ghost_writer = LLMAgent(
        llm=llm,
        system_prompt_path=REWRITE_SYSTEM_PROMPT_PATH,
        human_prompt_path=REWRITE_HUMAN_PROMPT_PATH,
    )

    work_descriptions = {}
    activity_descriptions = {}
    project_descriptions = {}
    selected_facts = ""

    logger.info("Rewriting work experience")
    for work in choosen_work:
        work_descriptions[work] = ghost_writer.invoke(
            block=parsed_profile["Work_experience"][work]["description"], job=job_offer).text
        selected_facts += f"{work} ({parsed_profile['Work_experience'][work]['company']}): {work_descriptions[work]}\n\n"
    logger.info("Rewriting activities")
    for activity in choosen_activities:
        activity_descriptions[activity] = ghost_writer.invoke(
            block=parsed_profile["Activities"][activity]["description"], job=job_offer).text
        selected_facts += f"{activity} ({parsed_profile['Activities'][activity]['organization']}): {activity_descriptions[activity]}\n\n"
    logger.info("Rewriting projects")
    for project in choosen_projects:
        project_descriptions[project] = ghost_writer.invoke(
            block=parsed_profile["Projects"][project]["description"], job=job_offer).text
        selected_facts += f"{project} ({parsed_profile['Projects'][project]['name']}): {project_descriptions[project]}\n\n"

    logger.info("Creating agent for about section")
    about_agent = LLMAgent(
        llm=llm,
        system_prompt_path=ABOUT_SYSTEM_PROMPT_PATH,
        human_prompt_path=ABOUT_HUMAN_PROMPT_PATH
    )

    logger.info("Rewriting about section")
    about = about_agent.invoke(
        job=job_offer, base_about=parsed_profile["About"], selected_facts=selected_facts, selected_skills=skills_result.categories)

    logger.info("Building profile")
    profile = build_profile(about=about.text,
                            education=choosen_education,
                            work_experience=work_descriptions,
                            projects=project_descriptions,
                            activities=activity_descriptions,
                            skills=skills_result,
                            job_schema_parser_result=parsed_profile)

    logger.info("Rendering CV")
    render_cv(profile, out_dir=Path(args.out_dir), template=args.template)


if __name__ == "__main__":
    main()
