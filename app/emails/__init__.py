"""Branded transactional email rendering.

Templates live under ``templates/<lang>/<name>.html`` and extend a shared
branded layout (EML-09: cream background, gold accent, serif type). Rendering
falls back to ``en`` when a language is missing. A plain-text alternative is
derived from the rendered HTML so every message is multipart.
"""

import html as html_lib
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_DEFAULT_LANG = "en"

# Per-template subjects, keyed by language with an ``en`` fallback.
SUBJECTS: dict[str, dict[str, str]] = {
    "confirmation": {"en": "Confirm your Rare Vintage email"},
    "password_reset": {"en": "Reset your Rare Vintage password"},
    "session_create": {"en": "New sign-in to your Rare Vintage account"},
    "label": {"en": "Your Rare Vintage account was updated"},
}


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


_HEAD_RE = re.compile(r"(?is)<head.*?</head>")
_BLOCK_RE = re.compile(r"(?is)<(style|script)\b.*?</\1>")
_TAG_RE = re.compile(r"<[^>]+>")


def _to_text(rendered_html: str) -> str:
    """A serviceable text/plain alternative derived from the HTML body."""
    body = _HEAD_RE.sub("", rendered_html)
    body = _BLOCK_RE.sub("", body)
    body = _TAG_RE.sub("", body)
    body = html_lib.unescape(body)
    lines = (line.strip() for line in body.splitlines())
    return "\n".join(line for line in lines if line).strip()


def _subject(template: str, lang: str) -> str:
    subjects = SUBJECTS.get(template, {})
    return subjects.get(lang) or subjects.get(_DEFAULT_LANG) or "Rare Vintage"


def _template_name(template: str, lang: str) -> str:
    candidate = f"{lang}/{template}.html"
    try:
        _env().get_template(candidate)
    except TemplateNotFound:
        return f"{_DEFAULT_LANG}/{template}.html"
    return candidate


def render_email(template: str, lang: str, context: dict[str, Any]) -> RenderedEmail:
    name = _template_name(template, lang)
    rendered = _env().get_template(name).render(**context)
    return RenderedEmail(subject=_subject(template, lang), html=rendered, text=_to_text(rendered))
