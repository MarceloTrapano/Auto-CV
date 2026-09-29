from typing import Any
from .structured_output import (
    ContactInfo as ContactInfo,
    SkillCategory as SkillCategory,
    Education as Education,
    WorkExperience as WorkExperience,
    Activity as Activity,
    Project as Project,
    CandidateProfile as CandidateProfile,
    SkillsResult as SkillsResult,
)


def build_profile(about: str,
                  education: list[str],
                  work_experience: dict[str, str] | None,
                  projects: dict[str, str] | None,
                  activities: dict[str, str] | None,
                  skills: SkillsResult,
                  job_schema_parser_result: dict[str, Any]):

    person_info = job_schema_parser_result["Person"]

    linkedin = person_info.get("linkedin", None)
    if linkedin is not None:
        linkedin_url = linkedin.split("\n")[0]
    else:
        linkedin_url = None

    contact_info = ContactInfo(full_name=person_info.get("name", ""),
                               email=person_info.get("email", None),
                               phone=person_info.get("phone", None),
                               github=person_info.get("github", None),
                               linkedin=linkedin_url)

    education_info = job_schema_parser_result["Education"]
    education_list = []

    for entry in education:
        parsed_education = Education(school_name=education_info[entry].get("school", ""),
                                     degree=education_info[entry].get(
                                         "degree", None),
                                     course=education_info[entry].get(
                                         "course", None),
                                     start_date=education_info[entry].get(
                                         "start", ""),
                                     end_date=education_info[entry].get(
                                         "end", None),
                                     responsibilities=["None"],
                                     )
        education_list.append(parsed_education)

    work_experience_info = job_schema_parser_result["Work_experience"]
    work_experience_list = []

    for key, item in work_experience.items():
        parsed_work_experience = WorkExperience(company_name=work_experience_info[key].get("company", ""),
                                                position=work_experience_info[key].get(
                                                    "position", ""),
                                                start_date=work_experience_info[key].get(
                                                    "start", ""),
                                                end_date=work_experience_info[key].get(
                                                    "end", None),
                                                responsibilities=item.split(
                                                    "- ")[1:],
                                                )
        work_experience_list.append(parsed_work_experience)

    projects_info = job_schema_parser_result["Projects"]
    projects_list = []

    for key, item in projects.items():
        technologies = projects_info[key].get("stack", "").split(",")
        parsed_projects = Project(project_name=projects_info[key].get("name", ""),
                                  technologies=technologies,
                                  project_description=item,
                                  link_to_repo=projects_info[key].get(
                                      "repo", None),
                                  )
        projects_list.append(parsed_projects)

    activities_info = job_schema_parser_result["Activities"]
    activities_list = []

    for key, item in activities.items():
        parsed_activities = Activity(organization=activities_info[key].get("organization", ""),
                                     role=activities_info[key].get("role", ""),
                                     start_date=activities_info[key].get(
                                         "start", ""),
                                     end_date=activities_info[key].get(
                                         "end", None),
                                     responsibilities=item.split("- ")[1:],
                                     )
        activities_list.append(parsed_activities)

    return CandidateProfile(contact_info=contact_info,
                            summary=about,
                            categorized_skills=skills,
                            work_experience=work_experience_list,
                            activities=activities_list,
                            projects=projects_list,
                            education=education_list)
