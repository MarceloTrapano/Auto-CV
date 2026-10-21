"""AutoCV web UI backend.

Run (from the project root, next to main.py):
    pip install fastapi uvicorn requests
    uvicorn server:app --reload
"""
import asyncio
import json
import logging
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
import types
import uuid
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any, get_args, get_origin, Union

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel

from main import (
    SKILL_SYSTEM_PROMPT_PATH, SKILL_HUMAN_PROMPT_PATH,
    ACTIVITY_SYSTEM_PROMPT_PATH, ACTIVITY_HUMAN_PROMPT_PATH,
    REWRITE_SYSTEM_PROMPT_PATH, REWRITE_HUMAN_PROMPT_PATH,
    ABOUT_SYSTEM_PROMPT_PATH, ABOUT_HUMAN_PROMPT_PATH, DEFAULT_TEMPLATE,
)
from src import (LLMAgent, JobSchemaParser, build_selection_schema,
                 SkillsResult, build_profile, CandidateProfile)
from src.render import render_tex, TEMPLATE_DIR
from src.scraper import NoFluffJobsStrategy, PracujStrategy, LinkedinStrategy

logger = logging.getLogger("autocv.server")
ROOT = Path(__file__).parent
JOBS_DIR = ROOT / "jobs"
JOBS_DIR.mkdir(exist_ok=True)
JOBS: dict[str, dict] = {}

# Temporary job folders (jobs/<id>/: cv.tex, cv.pdf, LaTeX aux files) are deleted
# after JOB_TTL seconds of inactivity. Override with AUTOCV_JOB_TTL_HOURS.
JOB_TTL = int(float(os.environ.get("AUTOCV_JOB_TTL_HOURS", "24")) * 3600)
CLEANUP_EVERY = 600  # seconds between sweeps


def _last_activity(d: Path, job: dict | None) -> float:
    """Newest of: last API use of the job and the mtime of any file in its folder."""
    t = job.get("last_used", 0.0) if job else 0.0
    try:
        t = max([t, d.stat().st_mtime] + [p.stat().st_mtime for p in d.iterdir()])
    except OSError:
        pass
    return t


def cleanup_jobs(ttl: int = JOB_TTL) -> int:
    """Remove job folders idle for longer than `ttl` seconds (ttl=0 removes all)."""
    removed, now = 0, time.time()
    for d in list(JOBS_DIR.iterdir()):
        if not d.is_dir():
            continue
        job = JOBS.get(d.name)
        if job and job["lock"].locked():  # LaTeX is compiling right now
            continue
        if ttl and now - _last_activity(d, job) < ttl:
            continue
        JOBS.pop(d.name, None)
        shutil.rmtree(d, ignore_errors=True)
        removed += 1
    if removed:
        logger.info("Removed %d job folder(s) from %s", removed, JOBS_DIR)
    return removed


def _cleanup_loop(stop: threading.Event) -> None:
    while not stop.wait(CLEANUP_EVERY):
        try:
            cleanup_jobs()
        except Exception:  # noqa: BLE001
            logger.exception("Job cleanup failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # JOBS lives in memory, so folders left by a previous run can never be used again.
    cleanup_jobs(ttl=0)
    stop = threading.Event()
    threading.Thread(target=_cleanup_loop, args=(stop,), daemon=True).start()
    yield
    stop.set()
    cleanup_jobs(ttl=0)


app = FastAPI(title="AutoCV", lifespan=lifespan)

FIT_SYSTEM_PROMPT = (
    "You are an expert career coach. Assess how well the candidate matches the "
    "given job offer based on the candidate's complete CV. Start with an overall "
    "fit score out of 10, then list concrete strengths, relevant evidence, gaps, "
    "and the highest-impact improvements. Do not invent experience or skills. "
    "Write in English, be concise and specific."
)

MODEL_FALLBACKS = {
    # Suggestions only. With an API key, /api/models enumerates the account's live catalogue.
    "gemini": [
        "gemini-4-argon", "gemini-3.8-flash", "gemini-3.7-flash",
        "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
        "gemini-3.1-pro-preview", "gemini-3-flash-preview",
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
    ],
    "openai": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "o3", "o3-mini", "o4-mini"],
    "anthropic": ["claude-opus-5-5", "claude-sonnet-4-5-20250929", "claude-3-7-sonnet-latest", "claude-3-5-haiku-latest"],
    "openai_compatible": [],
    "ollama": [],
}


class JobReq(BaseModel):
    # gemini | openai | anthropic | openai_compatible | ollama
    provider: str = "gemini"
    model: str
    api_key: str = ""
    base_url: str = ""
    num_ctx: int = 8192
    url: str
    schema_md: str
    template: str = DEFAULT_TEMPLATE


class RenderReq(BaseModel):
    profile: dict | None = None
    tex: str | None = None
    template: str = DEFAULT_TEMPLATE


class ModelListReq(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str = ""


def make_llm(req: JobReq):
    if req.provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=req.model, temperature=0, num_ctx=req.num_ctx,
                          base_url=req.base_url or "http://localhost:11434")
    if req.provider in {"openai", "openai_compatible"}:
        from langchain_openai import ChatOpenAI
        kw = {}
        if req.api_key:
            kw["api_key"] = req.api_key
        if req.base_url:
            kw["base_url"] = req.base_url
        return ChatOpenAI(model=req.model, temperature=0, **kw)
    if req.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kw = {"anthropic_api_key": req.api_key} if req.api_key else {}
        if req.base_url:
            kw["base_url"] = req.base_url
        return ChatAnthropic(model=req.model, temperature=0, **kw)
    from langchain_google_genai import ChatGoogleGenerativeAI
    kw = {"google_api_key": req.api_key} if req.api_key else {}
    return ChatGoogleGenerativeAI(model=req.model, temperature=0, **kw)


def pick_strategy(url: str):
    if "linkedin" in url:
        return LinkedinStrategy(url)
    if "nofluffjobs" in url:
        return NoFluffJobsStrategy(url)
    if "pracuj" in url:
        return PracujStrategy(url)
    raise ValueError(
        "Unsupported service. Supported: LinkedIn, NoFluffJobs, Pracuj.pl")


def compile_tex(job: dict, tex: str) -> None:
    with job["lock"]:
        d: Path = job["dir"]
        (d / "cv.tex").write_text(tex, encoding="utf-8")
        env = {**os.environ,
               "TEXINPUTS": f"{TEMPLATE_DIR}{os.pathsep}{os.environ.get('TEXINPUTS', '')}"}
        r = subprocess.run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
             "-output-directory=.", "cv.tex"],
            capture_output=True, text=True, cwd=d, env=env, timeout=180)
        if r.returncode != 0:
            raise RuntimeError(r.stdout[-2500:] or r.stderr[-2500:])


def fit_assessment(llm, offer: str, cv_text: str, about: str, skills, facts: str) -> str:
    prompt = (
        f"JOB OFFER:\n{offer[:8000]}\n\n"
        f"CANDIDATE'S COMPLETE SOURCE CV:\n{cv_text[:12000]}\n\n"
        f"GENERATED CV SUMMARY:\n{about[:2500]}\n\n"
        f"SELECTED SKILLS:\n{skills}\n\n"
        f"SELECTED EXPERIENCE AND PROJECT FACTS:\n{facts[:5000]}\n\n"
        "Assess the candidate's fit using evidence from the complete source CV. "
        "Clearly distinguish proven matches from missing or unclear evidence."
    )
    return llm.invoke([("system", FIT_SYSTEM_PROMPT), ("human", prompt)]).text


def pipeline(job: dict, req: JobReq) -> None:
    q: queue.Queue = job["q"]
    cur = {"s": "scrape"}

    def ev(stage, status, **data):
        job["last_used"] = time.time()
        if status == "running":
            cur["s"] = stage
        q.put({"stage": stage, "status": status, **data})

    try:
        ev("scrape", "running")
        offer = pick_strategy(req.url).scrap()
        job["offer"] = offer
        ev("scrape", "done", detail=offer,
           summary=f"Scraped offer ready to review ({len(offer):,} characters).")

        llm = make_llm(req)
        bio = req.schema_md
        path = job["dir"] / "profile.md"
        path.write_text(bio, encoding="utf-8")
        try:
            parsed = JobSchemaParser(str(path)).parse()
        finally:
            path.unlink(missing_ok=True)  # temporary copy of the profile, no longer needed

        ev("skills", "running")
        skills = LLMAgent(llm, SKILL_SYSTEM_PROMPT_PATH, SKILL_HUMAN_PROMPT_PATH
                          ).invoke_with_schema(SkillsResult, profile=bio, job=offer)
        ev("skills", "done", detail=skills.explanation)

        ev("select", "running")
        Selection = build_selection_schema(
            list(parsed["Work_experience"]), list(parsed["Activities"]),
            list(parsed["Education"]), list(parsed["Projects"]))
        sel = LLMAgent(llm, ACTIVITY_SYSTEM_PROMPT_PATH, ACTIVITY_HUMAN_PROMPT_PATH
                       ).invoke_with_schema(Selection, profile=bio, job=offer)
        labels = [("work", "Work experience", "Work_experience", ("company", "company_name", "position")),
                  ("activities", "Activities",
                   "Activities", ("organization", "role")),
                  ("education", "Education", "Education",
                   ("school", "school_name", "degree")),
                  ("projects", "Projects", "Projects", ("name", "project_name"))]

        def item_label(section, item_id, candidates):
            """Return a readable label for a selected item.

            Selection schema values are usually stable profile IDs such as
            ``Work-02`` (not numeric list indexes), because parsed profile
            sections are dictionaries keyed by those IDs.
            """
            entries = parsed.get(section, {})
            item = None
            if isinstance(entries, dict):
                item = entries.get(item_id)
                if item is None:
                    item = entries.get(str(item_id))
                # Also accept numeric IDs for older schema/parser variants.
                if item is None:
                    try:
                        numeric_id = int(item_id)
                        item = entries.get(
                            numeric_id, entries.get(str(numeric_id)))
                    except (TypeError, ValueError):
                        pass
            elif isinstance(entries, (list, tuple)):
                try:
                    idx = int(item_id)
                except (TypeError, ValueError):
                    idx = -1
                if 0 <= idx < len(entries):
                    item = entries[idx]

            fallback = f"{section.replace('_', ' ')} — {item_id}"
            if item is None:
                return fallback
            if isinstance(item, dict):
                primary = next((str(item.get(key, "")).strip() for key in candidates
                                if str(item.get(key, "")).strip()), "")
                secondary = str(item.get("position", "")).strip()
                if primary and secondary and secondary != primary and candidates[0] != "position":
                    return f"{primary} — {secondary}"
                return primary or fallback
            return str(item).strip() or fallback

        selection_blocks = []
        selection_briefs = []
        for key, label, section, name_candidates in labels:
            names = [item_label(section, item_id, name_candidates)
                     for item_id in getattr(sel, key)]
            selection_briefs.append(
                f"{label}: {', '.join(names) if names else 'None selected'}")
            selection_blocks.append(
                f"{label}:\n" +
                ("\n".join(f"- {name}" for name in names) if names else "- None selected") +
                f"\nReasoning: {getattr(sel, key + '_reasoning')}"
            )
        ev("select", "done", detail="\n\n".join(selection_blocks),
           summary=" | ".join(selection_briefs))

        ghost = LLMAgent(llm, REWRITE_SYSTEM_PROMPT_PATH,
                         REWRITE_HUMAN_PROMPT_PATH)
        name_key = {"Work_experience": "company",
                    "Activities": "organization", "Projects": "name"}
        descs = {"Work_experience": {}, "Activities": {}, "Projects": {}}
        facts = ""
        todo = [("Work_experience", sel.work), ("Activities", sel.activities),
                ("Projects", sel.projects)]
        for section, ids in todo:
            for i in ids:
                name = parsed[section][i][name_key[section]]
                ev("rewrite", "running",
                   detail=f"Rewriting {section.replace('_', ' ').lower()}: {name}…")
                txt = ghost.invoke(
                    block=parsed[section][i]["description"], job=offer).text
                descs[section][i] = txt
                facts += f"{name}: {txt}\n\n"
        ev("rewrite", "done",
           detail=f"Rewritten blocks: {sum(len(v) for v in descs.values())}")

        ev("about", "running")
        about = LLMAgent(llm, ABOUT_SYSTEM_PROMPT_PATH, ABOUT_HUMAN_PROMPT_PATH).invoke(
            job=offer, base_about=parsed["About"], selected_facts=facts,
            selected_skills=skills.categories)
        ev("about", "done", detail=about.text)

        ev("build", "running")
        profile = build_profile(
            about=about.text, education=sel.education,
            work_experience=descs["Work_experience"], projects=descs["Projects"],
            activities=descs["Activities"], skills=skills,
            job_schema_parser_result=parsed)
        ev("build", "done")
        q.put({"stage": "profile", "status": "done",
              "profile": profile.model_dump()})

        ev("render", "running", summary="Building the PDF document.")
        tex = render_tex(profile, template=req.template)
        compile_tex(job, tex)
        # The frontend can show the PDF and unlock editing as soon as this event arrives.
        ev("render", "done", tex=tex, summary="PDF compiled successfully.")

        def assess_fit_in_background():
            try:
                ev("fit", "running",
                   summary="The PDF is ready; AI assessment is running in the background.")
                fit = fit_assessment(llm, offer, bio, about.text,
                                     str(skills.categories), facts)
                ev("fit", "done", detail=fit,
                   summary="AI fit assessment completed.")
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "AI fit assessment failed after PDF compilation")
                ev("fit", "error",
                   detail=f"The PDF is ready, but the AI fit assessment failed: {exc}")
            finally:
                # A fit failure must not turn a successfully compiled PDF into a failed job.
                ev("end", "done")

        threading.Thread(target=assess_fit_in_background,
                         name=f"autocv-fit-{job['dir'].name}", daemon=True).start()
        return
    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline failed")
        ev(cur["s"], "error", detail=str(e))
        ev("end", "error")


@app.post("/api/jobs")
def create_job(req: JobReq):
    job_id = uuid.uuid4().hex[:10]
    d = JOBS_DIR / job_id
    d.mkdir(parents=True)
    job = {"q": queue.Queue(), "dir": d, "lock": threading.Lock(),
           "last_used": time.time()}
    JOBS[job_id] = job
    threading.Thread(target=pipeline, args=(job, req), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/events")
async def events(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "No such job")

    async def gen():
        loop = asyncio.get_running_loop()
        while True:
            item = await loop.run_in_executor(None, job["q"].get)
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            if item["stage"] == "end":
                break

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.post("/api/jobs/{job_id}/render")
def render(job_id: str, req: RenderReq):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "No such job")
    job["last_used"] = time.time()
    try:
        tex = req.tex if req.tex is not None else render_tex(
            CandidateProfile.model_validate(req.profile), template=req.template)
        compile_tex(job, tex)
        return {"ok": True, "tex": tex}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


@app.get("/api/jobs/{job_id}/cv.pdf")
def pdf(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "No such job (it may have expired)")
    job["last_used"] = time.time()
    f = job["dir"] / "cv.pdf"
    if not f.exists():
        raise HTTPException(404, "PDF does not exist yet")
    return FileResponse(f, media_type="application/pdf",
                        headers={"Cache-Control": "no-store"})


@app.post("/api/schema/parse")
def parse_schema(body: dict):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(body.get("text", ""))
    try:
        return JobSchemaParser(f.name).parse()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Failed to parse the file: {e}")
    finally:
        os.unlink(f.name)


def _sample_text(field_name: str) -> str:
    """Return plausible sample text for a field in a template preview CV."""
    key = field_name.lower()
    if "email" in key:
        return "alex.morgan@example.com"
    if "phone" in key or "mobile" in key:
        return "+1 555 010 2040"
    if "linkedin" in key:
        return "linkedin.com/in/alexmorgan"
    if "github" in key:
        return "github.com/alexmorgan"
    if any(word in key for word in ("repository", "repo", "website", "url", "link")):
        return "github.com/alexmorgan/open-data-explorer"
    if "company" in key or "employer" in key:
        return "Northstar Analytics"
    if "school" in key or "university" in key or "institution" in key:
        return "Northstar University"
    if "project" in key and "description" not in key:
        return "Open Data Explorer"
    if "organization" in key:
        return "Tech for Good"
    if "position" in key or "role" in key or "title" in key:
        return "Software Engineer"
    if "degree" in key:
        return "B.Sc. Computer Science"
    if "course" in key or "field_of_study" in key:
        return "Computer Science"
    if "category" in key:
        return "Programming Languages"
    if "start" in key or key in {"from", "start_date"}:
        return "06/2022"
    if "end" in key or key in {"to", "end_date"}:
        return "Present"
    if "summary" in key or key in {"about", "profile", "professional_summary"}:
        return ("Software engineer with 4+ years of experience building reliable, user-focused "
                "applications. Skilled in Python, APIs, data workflows, and cross-functional delivery.")
    if "description" in key or "about" in key:
        return "Designed and delivered practical features, improving reliability and user experience."
    if "responsib" in key or "bullet" in key or "achievement" in key:
        return "Built automated workflows that reduced repetitive work and improved consistency."
    if "hobb" in key or "interest" in key:
        return "Open-source projects, hiking, and data visualization"
    if "name" in key:
        return "Alex Morgan"
    if "skill" in key or "technolog" in key or "stack" in key:
        return "Python"
    return "Example"


def _sample_value(annotation: Any, field_name: str, depth: int = 0) -> Any:
    """Build a harmless, non-empty sample value for a Pydantic profile field."""
    if depth > 8:
        return None
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (Union, types.UnionType):
        choices = [arg for arg in args if arg is not type(None)]
        return _sample_value(choices[0], field_name, depth + 1) if choices else None

    if origin in (list, tuple, set):
        item_type = args[0] if args else str
        key = field_name.lower()
        if item_type is str:
            if any(word in key for word in ("responsib", "bullet", "achievement")):
                return [
                    "Built automated workflows that reduced repetitive work by 30%.",
                    "Collaborated with product and engineering teams to deliver reliable features.",
                ]
            if any(word in key for word in ("skill", "technolog", "stack", "tag")):
                return ["Python", "SQL", "Docker"]
            return [_sample_text(field_name)]
        sample = _sample_value(item_type, field_name, depth + 1)
        return [sample]

    if origin is dict:
        return {}

    try:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return _sample_model(annotation, depth + 1)
    except TypeError:
        pass

    try:
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return next(iter(annotation))
    except (TypeError, StopIteration):
        pass

    if annotation is str:
        return _sample_text(field_name)
    if annotation is bool:
        return False
    if annotation is int:
        return 4
    if annotation is float:
        return 4.0
    if annotation is Any:
        key = field_name.lower()
        if "categor" in key:
            return {"categories": [{"category_name": "Programming Languages", "skills": ["Python", "SQL"]}]}
        if "skill" in key or "technolog" in key:
            return ["Python", "SQL", "Docker"]
        return _sample_text(field_name)

    # Pydantic may leave a forward reference unresolved; a short placeholder
    # is safer than making template preview unavailable.
    return _sample_text(field_name)


def _sample_model(model_cls: type[BaseModel], depth: int = 0) -> BaseModel:
    values: dict[str, Any] = {}
    for name, field in model_cls.model_fields.items():
        try:
            values[name] = _sample_value(field.annotation, name, depth + 1)
        except Exception:  # noqa: BLE001
            values[name] = None
    return model_cls.model_construct(**values)


@app.get("/api/templates/preview.pdf")
def preview_template(template: str = DEFAULT_TEMPLATE):
    """Compile a sample CV with the selected real LaTeX template, without invoking AI."""
    try:
        available = {
            p.name for p in TEMPLATE_DIR.iterdir()
            if p.is_file() and p.name.endswith((".j2", ".tex.j2", ".tex"))
            and not p.name.startswith(".")
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Could not list templates: {exc}") from exc
    if template not in available:
        raise HTTPException(
            400, "Unknown template. Select one from the template list.")

    preview_dir = Path(tempfile.mkdtemp(prefix="autocv-template-preview-"))
    try:
        sample_profile = _sample_model(CandidateProfile)
        tex = render_tex(sample_profile, template=template)
        compile_tex({"dir": preview_dir, "lock": threading.Lock()}, tex)
        pdf_path = preview_dir / "cv.pdf"
        if not pdf_path.exists():
            raise RuntimeError(
                "The template compiled, but no PDF was created.")
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="template-preview.pdf",
            headers={"Cache-Control": "no-store"},
            background=BackgroundTask(
                shutil.rmtree, preview_dir, ignore_errors=True),
        )
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(preview_dir, ignore_errors=True)
        logger.exception("Template preview failed for %s", template)
        raise HTTPException(
            500, f"Could not preview this template: {exc}") from exc


@app.get("/api/templates")
def templates():
    try:
        items = sorted({p.name for p in TEMPLATE_DIR.iterdir()
                        if p.is_file() and p.name.endswith((".j2", ".tex.j2", ".tex"))
                        and not p.name.startswith(".")})
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Could not list templates: {e}")
    if not items:
        items = [DEFAULT_TEMPLATE]
    return {"templates": items}


@app.post("/api/models")
def list_provider_models(req: ModelListReq):
    """Discover models available from a provider; credentials are accepted in the POST body only."""
    provider = req.provider
    if provider == "ollama":
        base = (req.base_url or "http://localhost:11434").rstrip("/")
        try:
            response = requests.get(base + "/api/tags", timeout=10)
            response.raise_for_status()
            models = sorted(
                {m["name"] for m in response.json().get("models", []) if m.get("name")})
            return {"models": models, "source": "remote"}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                502, f"Cannot list Ollama models: {exc}") from exc

    if provider not in {"gemini", "openai", "anthropic", "openai_compatible"}:
        raise HTTPException(400, "Unsupported model provider")

    api_key = req.api_key.strip()
    base_url = req.base_url.strip().rstrip("/")
    if not api_key:
        env_name = {"gemini": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY",
                    "anthropic": "ANTHROPIC_API_KEY"}.get(provider)
        api_key = os.environ.get(env_name, "") if env_name else ""
    if not api_key and provider != "openai_compatible":
        return {"models": MODEL_FALLBACKS.get(provider, []), "source": "defaults",
                "warning": "Enter an API key to load the full live model catalogue. Showing common model IDs for now."}

    try:
        models: list[str] = []
        if provider == "gemini":
            page_token = None
            # Follow provider pagination rather than silently showing only page one.
            for _ in range(20):
                params = {"pageSize": 1000}
                if page_token:
                    params["pageToken"] = page_token
                response = requests.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params=params, headers={"x-goog-api-key": api_key}, timeout=15)
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("models", []):
                    name = item.get("name", "").removeprefix("models/")
                    methods = item.get("supportedGenerationMethods", [])
                    # Keep models that can generate text/content, not embedding-only models.
                    if name and "generateContent" in methods:
                        models.append(name)
                page_token = payload.get("nextPageToken")
                if not page_token:
                    break
        elif provider == "anthropic":
            endpoint = base_url or "https://api.anthropic.com"
            endpoint = endpoint if endpoint.endswith(
                "/v1") else endpoint + "/v1"
            after_id = None
            for _ in range(20):
                params = {"limit": 100}
                if after_id:
                    params["after_id"] = after_id
                response = requests.get(
                    endpoint + "/models", params=params,
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}, timeout=15)
                response.raise_for_status()
                payload = response.json()
                page = payload.get("data", [])
                models.extend(item.get("id", "") for item in page)
                if not payload.get("has_more") or not page:
                    break
                after_id = payload.get("last_id") or page[-1].get("id")
                if not after_id:
                    break
        else:
            endpoint = base_url or (
                "https://api.openai.com/v1" if provider == "openai" else "")
            if not endpoint:
                return {"models": [], "source": "remote",
                        "warning": "Enter a base URL for the OpenAI-compatible API."}
            if not endpoint.endswith("/v1"):
                endpoint += "/v1"
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            response = requests.get(
                endpoint + "/models", headers=headers, timeout=15)
            response.raise_for_status()
            models = [item.get("id", "")
                      for item in response.json().get("data", [])]

        models = sorted({model.strip()
                        for model in models if model and model.strip()})
        if not models:
            return {"models": MODEL_FALLBACKS.get(provider, []), "source": "defaults",
                    "warning": "The provider returned no usable text-generation models. Showing suggested IDs instead."}
        return {"models": models, "source": "remote"}
    except Exception as exc:  # noqa: BLE001
        logger.info("Model discovery failed for %s (%s)",
                    provider, type(exc).__name__)
        fallback = MODEL_FALLBACKS.get(provider, [])
        status = getattr(getattr(exc, "response", None), "status_code", None)
        reason = f"HTTP {status}" if status else "a connection or provider error"
        return {"models": fallback, "source": "defaults",
                "warning": f"Live model discovery failed ({reason}). Showing suggested IDs; you can also enter a custom model ID."}


@app.get("/api/ollama/models")
def ollama_models(base_url: str = "http://localhost:11434"):
    try:
        r = requests.get(base_url.rstrip("/") + "/api/tags", timeout=3)
        r.raise_for_status()
        return {"models": [m["name"] for m in r.json().get("models", [])]}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Cannot connect to Ollama: {e}")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
