<div align="center">

# 📄 Auto-CV

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-fast-magenta)](https://github.com/astral-sh/uv)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-black)](https://ollama.com/)
[![LaTeX](https://img.shields.io/badge/output-LaTeX-green)](https://www.latex-project.org/)

*A Python-based tool that tailors your CV to a specific job offer. You describe your entire career once in a structured biography file, and Auto-CV uses a local LLM to pick the most relevant parts, rewrite them for the target position and render the result through a LaTeX template.*

</div>

---

## ⚙️ How it works

Auto-CV takes two inputs: a biography file (see [Job schema](#-job-schema)) and a job offer saved as plain text. Everything runs locally through [Ollama](https://ollama.com/), so your personal data never leaves your machine.

The pipeline consists of six steps:

### 1. Parse the Biography

The biography file is parsed into a structured profile (person, education, work experience, projects, activities, skills, hobbies). Every entry gets a unique ID such as `Work-01` or `Proj-02`.

### 2. Extract Relevant Skills

An LLM agent compares your skills with the job offer and returns them as a structured, categorized result. Only skills that matter for the position make it to the final CV.

### 3. Select the Best Entries

A second agent chooses which work experiences, activities, education entries and projects are the most relevant for the offer. The output is constrained to a schema built dynamically from the IDs found in your biography, so the model can only select entries that actually exist and cannot invent new ones.

### 4. Rewrite Descriptions

Each selected work experience, activity and project is rewritten by a "ghost writer" agent to highlight what the employer is looking for, based strictly on the facts from your original description.

### 5. Generate the About Section

A final agent writes a short, personalized "About me" section using your base summary, the job offer, the selected facts and the selected skills.

### 6. Render the CV

The tailored profile is passed to a [Jinja2](https://jinja.palletsprojects.com/) template and rendered into a ready-to-compile LaTeX document.

---

## 🛠️ Prerequisites & Installation

The project requires:

- **Python 3.11** or newer
- **[Ollama](https://ollama.com/)** installed and running
- A LaTeX distribution (e.g. TeX Live, MiKTeX) to compile the generated `.tex` file into a PDF

It is highly recommended to run the project using the [uv package manager](https://github.com/astral-sh/uv):

```bash
uv sync
```

Then pull the model used by default:

```bash
ollama pull qwen2.5:3b-instruct
```

> 💡 The model is configured in `main.py`. The default `qwen2.5:3b-instruct` is small and fast, but larger models (for example `qwen3:30b-a3b`) will give noticeably better rewrites if your hardware allows it.

---

## 🚀 How to run it

Prepare your biography file and save the job offer as a `.txt` file, then run:

```bash
uv run main.py job_schema.md job_offer.txt
```

You can also customize the output directory and the template:

```bash
uv run main.py job_schema.md job_offer.txt --out-dir build --template cv.tex.j2
```

#### 📋 CLI Arguments:

- `filename` : Path to the candidate profile (biography) file (required)

- `job_offer` : Path to the job offer `.txt` file (required)

- `--out-dir` : Output directory for the generated CV (default: `build`)

- `--template` : Name of the Jinja template used for rendering (default: `cv.tex.j2`)

---

## 🧾 Job schema

`job_schema.md` is an example biography file that shows the exact format Auto-CV expects. The parser relies on this structure, so it has to be preserved - otherwise the profile will not be read correctly. Replace the sample content (a fictional medical student profile) with your own data, but keep the section names, the field names and the ID numbering.

### Sections

| Section | Heading | Fields |
| ------- | ------- | ------ |
| **About** | `## About` | Free text: a short summary of who you are and what you are looking for |
| **Person** | `## Person` | `name`, `email`, `phone`, `github`, `linkedin` |
| **Education** | `## Edu-01`, `## Edu-02`, … | `school`, `degree`, `course`, `start`, `end`, `description` |
| **Work experience** | `## Work-01`, `## Work-02`, … | `company`, `position`, `start`, `end`, `description` |
| **Projects** | `## Proj-01`, `## Proj-02`, … | `name`, `stack`, `repo`, `description` |
| **Activities** | `## Act-01`, `## Act-02`, … | `organization`, `role`, `start`, `end`, `description` |
| **Skills** | `## Skills` | `Languages`, `Certifications`, `Tools & Systems`, `Proficiency notes` |
| **Hobbies** | `## Hobbies` | Additional hobbies |

### Example entry

```markdown
## Work-01

company: Johns Hopkins Hospital
position: Clinical Research Assistant (Internal Medicine)
start: 06/2021
end: 08/2021
description:
Joined a clinical research team of 6 investigating patient triage efficiency
in the emergency department. Replaced paper-based intake surveys with a digital
data collection pipeline, cutting daily review time from 3 hours to under
20 minutes.
```

### Rules to keep in mind

- Every entry needs its own heading with a unique, sequential ID (`Edu-01`, `Work-03`, `Proj-02`, …). These IDs are what the LLM uses to select the entries.
- Use the `key: value` format for fields and do not rename the keys.
- Dates are written as `MM/YYYY`.
- The more concrete your descriptions are (numbers, tools, results), the better the rewritten CV will be. The LLM only works with the facts you provide.

---

## 🎨 Templates

CVs are generated from Jinja2 templates written in LaTeX. The default one is `cv.tex.j2`, and you can point Auto-CV to a different one with the `--template` argument.

You do not need to write LaTeX by hand to get a new look. Templates can be generated with a stronger LLM - for example Claude Sonnet 5.5, which is available for free. Give it the default template as a reference (so the placeholders stay compatible with the renderer) and describe the style you want, such as a two-column layout, a different color scheme or a more compact design. Save the result in the templates folder and run Auto-CV with `--template your_template.tex.j2`.