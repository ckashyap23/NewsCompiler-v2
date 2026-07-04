"""Compile stored research entries into a weekly newsletter with OpenAI."""
import json
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from llm_provider import get_llm_config

load_dotenv()

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_SKILL_PATH = REPO_ROOT / "skills" / "topic-newsletter-compiler" / "SKILL.md"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas" / "newsletter_compiler_result.json"


class NewsletterCompilerError(RuntimeError):
    """Raised when newsletter compilation cannot complete."""


def _load_text_file(path: str | Path, label: str) -> str:
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"{label} file not found: {resolved}")

    text = resolved.read_text(encoding="utf-8").strip()
    if not text:
        raise NewsletterCompilerError(f"{label} file is empty: {resolved}")
    return text


def _load_schema(path: str | Path) -> dict:
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Schema file not found: {resolved}")
    return json.loads(resolved.read_text(encoding="utf-8"))


def _validate_newsletter_payload(payload: dict, schema: dict) -> dict:
    if not isinstance(payload, dict):
        raise NewsletterCompilerError("OpenAI backend did not return a JSON object.")

    required = schema.get("required") or []
    for field in required:
        if field not in payload:
            raise NewsletterCompilerError(f"Newsletter result is missing `{field}`.")

    for field in (
        "newsletter_title",
        "opening_hook",
        "thesis",
        "my_read",
        "newsletter_markdown",
        "newsletter_html",
        "linkedin_post",
    ):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise NewsletterCompilerError(f"`{field}` must be a non-empty string.")

    for field in ("key_trends", "top_highlights", "topics_covered"):
        if not isinstance(payload.get(field), list):
            raise NewsletterCompilerError(f"`{field}` must be a list.")

    return payload


def _build_newsletter_prompt(research_entries: list[dict]) -> str:
    """Build the prompt for the newsletter compiler skill."""
    entries_json = json.dumps(research_entries, indent=2)
    return (
        "Analyze the following week of research entries and compile them into a professional "
        "newsletter suitable for LinkedIn. Identify key trends, top highlights, and implications "
        "for the audience. Return structured JSON matching the expected schema.\n\n"
        "Research Entries:\n"
        f"{entries_json}"
    )


def compile_newsletter(
    research_entries: list[dict],
    skill_path: Optional[str | Path] = None,
) -> dict:
    """
    Compile a weekly newsletter from research entries using OpenAI.

    Args:
        research_entries: List of research entry dicts with keys: datetime, topic, content
        skill_path: Optional path to the newsletter-compiler skill file

    Returns:
        Dictionary containing compiled newsletter with keys:
        - newsletter_title
        - opening_hook
        - key_trends
        - top_highlights
        - thesis
        - my_read
        - topics_covered
        - newsletter_markdown
        - newsletter_html
        - linkedin_post

    Raises:
        NewsletterCompilerError: If OpenAI is not configured or compilation fails
        ValueError: If research_entries is empty or invalid
    """
    if not research_entries:
        raise ValueError("research_entries cannot be empty")

    if not isinstance(research_entries, list):
        raise ValueError("research_entries must be a list of dicts")

    # Ensure entries have required fields
    for entry in research_entries:
        if not isinstance(entry, dict):
            raise ValueError("Each entry must be a dictionary")
        if "topic" not in entry or "content" not in entry:
            raise ValueError("Each entry must have 'topic' and 'content' fields")

    instructions = _load_text_file(skill_path or DEFAULT_SKILL_PATH, "Skill")
    schema = _load_schema(DEFAULT_SCHEMA_PATH)
    prompt = _build_newsletter_prompt(research_entries)

    try:
        llm = get_llm_config("newsletter_compile", "gpt-4o-mini")
    except RuntimeError as exc:
        raise NewsletterCompilerError(str(exc)) from exc

    client = llm.client
    model = llm.model
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "newsletter_compiler_result",
                "schema": schema,
                "strict": True,
            }
        },
    )

    raw_text = (getattr(response, "output_text", "") or "").strip()
    if not raw_text:
        raise NewsletterCompilerError("OpenAI backend returned an empty response.")

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise NewsletterCompilerError("OpenAI backend did not return valid structured JSON.") from exc

    result = _validate_newsletter_payload(result, schema)
    logger.info("Successfully compiled newsletter")
    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Test with sample data
    test_entries = [
        {
            "id": 1,
            "datetime": "2026-06-01T09:00:00",
            "topic": "AI Enterprise Adoption 2026",
            "content": "Enterprise adoption of large language models continues to accelerate. "
                      "Companies are moving beyond pilot projects to production deployments.",
        },
        {
            "id": 2,
            "datetime": "2026-06-02T09:00:00",
            "topic": "GPU Shortage Resolution",
            "content": "NVIDIA's expanded production capacity has eased GPU shortages. "
                      "Prices have stabilized and availability has improved significantly.",
        },
    ]
    
    try:
        result = compile_newsletter(test_entries)
        print("\n=== Newsletter Compiled ===\n")
        print(result.get("newsletter_markdown", "No markdown content"))
    except Exception as e:
        logger.error(f"Failed to compile newsletter: {e}", exc_info=True)
