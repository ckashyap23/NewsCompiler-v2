from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class ToolPolicy:
    enable_web_search: bool = False
    web_search_tool_name: str = "web_search"


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    instructions_path: Path
    instructions: str


@dataclass(frozen=True)
class SkillRequest:
    topic: str
    prompt: str
    output_schema_path: Path
    return_response: bool = False


@dataclass(frozen=True)
class SkillResult:
    text: str
    payload: dict
    backend: str


class SkillRuntimeError(RuntimeError):
    """Raised when a backend cannot satisfy a skill request."""


def load_skill(skill_path: str | Path, name: str) -> SkillDefinition:
    instructions_path = Path(skill_path)
    if not instructions_path.exists():
        raise FileNotFoundError(f"Skill file not found: {instructions_path}")

    instructions = instructions_path.read_text(encoding="utf-8").strip()
    if not instructions:
        raise SkillRuntimeError(f"Skill file is empty: {instructions_path}")

    return SkillDefinition(
        name=name,
        instructions_path=instructions_path,
        instructions=instructions,
    )


def load_schema(schema_path: str | Path) -> dict:
    resolved = Path(schema_path)
    if not resolved.exists():
        raise FileNotFoundError(f"Schema file not found: {resolved}")
    return json.loads(resolved.read_text(encoding="utf-8"))


def normalize_payload(payload: dict, *, topic: str, schema: dict) -> dict:
    normalized = dict(payload or {})

    summary = str(normalized.get("summary_markdown") or "").strip()
    if not summary:
        raise SkillRuntimeError("Structured result is missing `summary_markdown`.")

    subject = str(normalized.get("subject") or "").strip()
    if not subject:
        subject = f"Topic Research: {topic[:80]}".strip()

    raw_sources = normalized.get("sources")
    sources = raw_sources if isinstance(raw_sources, list) else []
    cleaned_sources = []
    for item in sources:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title or not url:
            continue
        cleaned = {"title": title, "url": url}
        date = str(item.get("date") or "").strip()
        if date:
            cleaned["date"] = date
        cleaned_sources.append(cleaned)

    normalized = {
        "summary_markdown": summary,
        "subject": subject,
        "sources": cleaned_sources,
    }
    _validate_against_schema(normalized, schema)
    return normalized


def _validate_against_schema(payload: dict, schema: dict) -> None:
    required = schema.get("required") or []
    for field in required:
        if field not in payload:
            raise SkillRuntimeError(f"Structured result is missing required field `{field}`.")

    if not isinstance(payload.get("summary_markdown"), str) or not payload["summary_markdown"].strip():
        raise SkillRuntimeError("`summary_markdown` must be a non-empty string.")
    if not isinstance(payload.get("subject"), str) or not payload["subject"].strip():
        raise SkillRuntimeError("`subject` must be a non-empty string.")
    if not isinstance(payload.get("sources"), list):
        raise SkillRuntimeError("`sources` must be a list.")

    for source in payload["sources"]:
        if not isinstance(source, dict):
            raise SkillRuntimeError("Each source must be an object.")
        if not str(source.get("title") or "").strip():
            raise SkillRuntimeError("Each source must include a non-empty `title`.")
        if not str(source.get("url") or "").strip():
            raise SkillRuntimeError("Each source must include a non-empty `url`.")
