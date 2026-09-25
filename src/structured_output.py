from pydantic import BaseModel, Field
from typing import Literal


def build_selection_schema(work_ids, act_ids, edu_ids, proj_ids):
    WorkId = Literal[tuple(work_ids)] if work_ids else None
    ActId = Literal[tuple(act_ids)] if act_ids else None
    EduId = Literal[tuple(edu_ids)] if edu_ids else None
    ProjId = Literal[tuple(proj_ids)] if proj_ids else None

    class Selection(BaseModel):
        work_reasoning: str = Field(max_length=300)
        work: list[WorkId] = Field(max_length=3)
        activities_reasoning: str = Field(max_length=300)
        activities: list[ActId] = Field(max_length=3)
        education_reasoning: str = Field(max_length=300)
        education: list[EduId] = Field(max_length=3)
        projects_reasoning: str = Field(max_length=300)
        projects: list[ProjId] = Field(max_length=3)

    return Selection


class ContactInfo(BaseModel):
    full_name: str = Field(description="Candidate's full name")
    email: str | None = Field(
        default=None, description="Candidate's email address")
    phone: str | None = Field(
        default=None, description="Candidate's phone number with country code")
    github: str | None = Field(
        default=None, description="GitHub profile URL or username")
    linkedin: str | None = Field(
        default=None, description="LinkedIn profile URL")


class SkillCategory(BaseModel):
    category_name: str = Field(
        description="Category name in English, e.g., 'Programming Languages', 'ML / AI', 'Databases & Vector Stores', 'DevOps & Tools'"
    )
    skills: list[str] = Field(
        description="List of skills , languages with proficiency, specific technologies, frameworks, or libraries in this category"
    )


class SkillsResult(BaseModel):
    categories: list[SkillCategory] = Field(
        description="Skills grouped by category, matched between the candidate profile and the job offer. Return an empty list if none match."
    )


class Education(BaseModel):
    school_name: str = Field(
        description="University or school name in English, e.g., 'Poznań University of Technology'"
    )
    degree: str | None = Field(
        default=None,
        description="Degree obtained, e.g., 'Bachelor of Science', 'Master of Science', 'Engineering Degree'"
    )
    course: str | None = Field(
        default=None,
        description="Field of study or major, e.g., 'Computer Science', 'Robotics'"
    )
    start_date: str = Field(
        description="Start date, e.g., '10/2021' or '2021'")
    end_date: str | None = Field(
        default=None,
        description="End date, or 'Present' if currently studying"
    )
    responsibilities: list[str] = Field(
        description="List of bullet points describing key achievements, tasks, and technologies used, tailored to the target job offer"
    )


class WorkExperience(BaseModel):
    company_name: str = Field(
        description="Company or organization name, e.g., 'Amazon', 'Meta'")
    position: str = Field(
        description="Job title/role held, e.g., 'Python Developer Intern', 'AI Software Engineer'"
    )
    start_date: str = Field(
        description="Employment start date, e.g., '01/2023' or 'Jan 2023'")
    end_date: str | None = Field(
        default=None,
        description="Employment end date, or 'Present' if currently employed"
    )
    responsibilities: list[str] = Field(
        description="List of bullet points describing key achievements, tasks, and technologies used, tailored to the target job offer"
    )


class Activity(BaseModel):
    organization: str = Field(
        description="Name of organization"
    )
    role: str = Field(
        description="Role held in organization"
    )
    start_date: str = Field(
        description="Participation start date., '01/2023' or 'Jan 2023'"
    )
    end_date: str = Field(
        description="Participation end date, or 'Present' if participating ., '01/2023' or 'Jan 2023'"
    )
    responsibilities: list[str] = Field(
        description="List of bullet points describing key achievements, tasks, and technologies used, tailored to the target job offer"
    )


class Project(BaseModel):
    project_name: str = Field(description="Name of the project")
    technologies: list[str] = Field(
        default_factory=list,
        description="List of core technologies used, e.g., ['Python', 'ROS2', 'FastAPI']"
    )
    project_description: str = Field(
        description="Concise description (2-3 sentences) highlighting functionality, results, and relevance to the target job offer"
    )
    link_to_repo: str | None = Field(
        default=None,
        description="Optional URL to the GitHub repository or live demo"
    )


class CandidateProfile(BaseModel):
    primary_role: str = Field(
        description="Target professional title in English, e.g., 'Junior AI / Software Engineer'")
    contact_info: ContactInfo = Field(
        description="Candidate's contact details")
    summary: str = Field(
        description="A compelling 2-3 sentence executive summary tailored strictly to the target job description"
    )
    categorized_skills: SkillsResult = Field(
        description="Technical skills grouped into logical categories"
    )
    work_experience: list[WorkExperience] = Field(
        description="Candidate's work history listed chronologically"
    )
    activities: list[Activity] = Field(
        description="Selected relevant activities matching the requirements of the job offer"
    )
    projects: list[Project] = Field(
        description="Selected relevant projects matching the requirements of the job offer"
    )
    education: list[Education] = Field(
        description="Candidate's educational background"
    )
