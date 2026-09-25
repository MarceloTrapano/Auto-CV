import argparse
import os
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from typing import Literal
from pydantic import BaseModel, Field

from src import LLMAgent, JobSchemaParser, build_selection_schema


job_mock = """Główne obowiązki (Czego się nauczysz i w czym będziesz nas wspierać):


    Raportowanie zarządcze: Nauka tworzenia i przygotowywania miesięcznych raportów dla kadry zarządzającej. 
    Zamknięcie miesiąca: Aktywne wsparcie zespołu w comiesięcznym procesie zamykania i raportowania wyników finansowych.
    Kalkulacja i monitoring KPI: Obliczanie i śledzenie kluczowych wskaźników efektywności (KPI) dla obszaru usług finansowych.
    Analiza danych i rekomendacje: Badanie odchyleń oraz ich przyczyn. Nauczysz się wyciągać wnioski na podstawie danych historycznych i proponować konkretne działania poprawiające wyniki.


Główne wyzwania (Z czym będziesz się mierzyć):


    Optymalizacja i automatyzacja raportowania: Zmierzysz się ze złożonością danych finansowych. Liczymy na Twoją ciekawość w poszukiwaniu nowych sposobów na poprawę efektywności oraz automatyzację procesu generowania raportów.
    Praca z Big Data, SQL i AI: Zmierzysz się z różnorodnymi, wielkimi zbiorami danych. Wyzwaniem będzie nauka i wykorzystywanie zapytań SQL, statystyki oraz narzędzi opartych na sztucznej inteligencji (AI) do analizy, weryfikacji i obsługi tych danych.


Profil kandydata, którego szukamy:


    Status studenta lub wykształcenie wyższe (np. Ekonomia, Finanse i Rachunkowość, Matematyka, Metody Ilościowe, Big Data, Analiza Danych lub pokrewne).
    Zmysł analityczny i krytyczne myślenie: Nastawienie na pracę z danymi (data-driven mindset).
    Wybitna dbałość o szczegóły: Skrupulatność, dokładność oraz poczucie estetyki – kluczowe do tworzenia czytelnych i profesjonalnych raportów zarządczych.
    Ciągły apetyt na usprawnienia: Proaktywność, ciekawość technologiczna i chęć automatyzowania powtarzalnych procesów.
    Nowoczesny warsztat analityka: Chęć do nauki (lub już posiadana wiedza) z zakresu Big Data, analizy statystycznej oraz języka SQL.
    Otwartość na AI: Gotowość do eksplorowania i codziennego wykorzystywania narzędzi sztucznej inteligencji (AI) wspomagających analitykę i raportowanie.
    Podstawy finansów: Wiedza z zakresu planowania finansowego i controllingu.


Ze swojej strony oferujemy:


    Wiedzę ekspercką: Będziesz uczyć się od doświadczonych specjalistów, otrzymując wskazówki i wsparcie w rozwijaniu swoich umiejętności i wiedzy z zakresu finansów.
    Zespół oparty na współpracy: Staniesz się częścią przyjaznego i wspierającego zespołu, w którym wysoko ceni się współpracę i dzielenie się wiedzą.
    Dostęp do najnowocześniejszych systemów: Będziesz pracować z zaawansowanym oprogramowaniem i systemami, zdobywając cenną wiedzę techniczną.
    Elastyczny czas pracy – dostosowany do Twojego codziennego harmonogramu zajęć
    Nowoczesne środowisko pracy: Ciesz się naszymi wygodnymi i nowoczesnymi biurami, zaprojektowanymi tak, aby sprzyjać współpracy i kreatywności."""


PROMPT_FOLDER = os.path.abspath(os.path.join("src", "prompts"))

SKILL_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "skills_system.md")
SKILL_HUMAN_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "skills_human.md")

ACTIVITY_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "activity_system.md")
ACTIVITY_HUMAN_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "activity_human.md")

REWRITE_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "rewrite_system.md")
REWRITE_HUMAN_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "rewrite_human.md")

ABOUT_SYSTEM_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "about_system.md")
ABOUT_HUMAN_PROMPT_PATH = os.path.join(PROMPT_FOLDER, "about_human.md")


def main():
    parser = argparse.ArgumentParser(prog="AutoCV",
                                     description="Generate CV from candidate profile based on job offer")
    parser.add_argument("filename")
    args = parser.parse_args()

    with open(args.filename, "r", encoding="utf-8") as file:
        biography = file.read()

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

    skills_result = skill_extractor.invoke(profile=biography, job=job_mock)

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
        Selection, profile=biography, job=job_mock)

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
            block=parsed_profile["Work_experience"][work]["description"], job=job_mock).content
        selected_facts += f"{work} ({parsed_profile['Work_experience'][work]['company']}): {work_descriptions[work]}\n\n"
    for activity in choosen_activities:
        activity_descriptions[activity] = ghost_writer.invoke(
            block=parsed_profile["Activities"][activity]["description"], job=job_mock).content
        selected_facts += f"{activity} ({parsed_profile['Activities'][activity]['organization']}): {activity_descriptions[activity]}\n\n"
    for project in choosen_projects:
        project_descriptions[project] = ghost_writer.invoke(
            block=parsed_profile["Projects"][project]["description"], job=job_mock).content
        selected_facts += f"{project} ({parsed_profile['Projects'][project]['name']}): {project_descriptions[project]}\n\n"

    about_agent = LLMAgent(
        llm=llm,
        system_prompt_path=ABOUT_SYSTEM_PROMPT_PATH,
        human_prompt_path=ABOUT_HUMAN_PROMPT_PATH
    )

    about = about_agent.invoke(
        job=job_mock, base_about=parsed_profile["About"], selected_facts=selected_facts, selected_skills=skills_result.content.split("Explanation (do not output it):")[0])

    print(about.content)
    print("#"*25)
    print(choosen_education)
    if work_descriptions:
        print(work_descriptions)
    if activity_descriptions:
        print(activity_descriptions)
    if project_descriptions:
        print(project_descriptions)
    print(skills_result.content)


if __name__ == "__main__":
    main()
