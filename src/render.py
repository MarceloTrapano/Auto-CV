# Render generated with Claude

import re
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

_SPECIAL = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def tex(value) -> str:
    """Escapes LaTeX special characters."""
    if value is None:
        return ""
    return "".join(_SPECIAL.get(c, c) for c in str(value).strip())


def url_arg(value) -> str:
    """Escapes a URL used as the first argument of \\href."""
    return str(value).strip().replace("%", r"\%").replace("#", r"\#")


def paras(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]


def bullets(items) -> list[str]:
    """Str (lines) or list -> clean list of items without '-' and 'None'."""
    if isinstance(items, str):
        items = items.splitlines()
    out = []
    for item in items or []:
        s = re.sub(r"^\s*[-•*–]\s*", "", str(item)).strip()
        if s and s.lower() != "none":
            out.append(s)
    return out


def mon_year(value) -> str:
    """'06/2021' -> 'Jun 2021'; empty / None -> 'present'."""
    if not value or str(value).strip().lower() in {"present", "none"}:
        return "present"
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{4})\s*", str(value))
    if m and 1 <= int(m[1]) <= 12:
        return f"{_MONTHS[int(m[1]) - 1]} {m[2]}"
    return str(value).strip()


def year(value) -> str:
    """'08/2023' -> '2023'; empty / None -> 'present'."""
    m = re.search(r"\d{4}", str(value or ""))
    return m.group(0) if m else "present"


def _https(url: str) -> str:
    url = url.strip()
    return url if url.startswith(("http://", "https://")) else "https://" + url


def build_contacts(c) -> list[dict]:
    """Header links: icon macro, url, label. Missing fields are skipped."""
    out = []
    if c.github:
        u = _https(c.github)
        out.append({"icon": r"\faGithub", "url": u,
                    "label": u.rstrip("/").split("/")[-1]})
    if c.linkedin:
        out.append({"icon": r"\faLinkedin", "url": _https(c.linkedin),
                    "label": "Linkedin"})
    if c.email:
        out.append({"icon": r"\faEnvelope", "url": f"mailto:{c.email.strip()}",
                    "label": c.email.strip()})
    if c.phone:
        out.append({"icon": r"\faMobile",
                    "url": "tel:" + re.sub(r"[^\d+]", "", c.phone),
                    "label": c.phone.strip()})
    return out


env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    block_start_string="((*", block_end_string="*))",
    variable_start_string="(((", variable_end_string=")))",
    comment_start_string="((=", comment_end_string="=))",
    trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
    autoescape=False,
    undefined=StrictUndefined,
)
env.filters.update(tex=tex, url_arg=url_arg, paras=paras, bullets=bullets,
                   mon_year=mon_year, year=year)


def render_tex(profile, template: str = "cv.tex.j2") -> str:
    return env.get_template(template).render(
        p=profile, contacts=build_contacts(profile.contact_info))


def render_cv(profile, out_dir: str | Path = Path(__file__).parent.parent / "build", compile_pdf: bool = True, template: str = "cv.tex.j2") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tex_path = out / \
        f"{profile.contact_info.full_name.split(" ")[0]}_{profile.contact_info.full_name.split(" ")[-1]}_cv.tex"
    tex_path.write_text(render_tex(
        profile, template=template), encoding="utf-8")
    if not compile_pdf:
        return tex_path

    res = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
         f"-output-directory={out}", str(tex_path)],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise RuntimeError("LaTeX compilation failed:\n" + res.stdout[-2000:])
    return out / "cv.pdf"
