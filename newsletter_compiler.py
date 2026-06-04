"""
Newsletter compiler: Use OpenAI to analyze recent research data and create a newsletter.

This module integrates with the skill runtime to process research entries using
the "topic-newsletter-compiler" skill with OpenAI as the backend.
"""
import json
import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from skill_runtime import (
    SkillRequest,
    SkillRuntimeError,
    ToolPolicy,
    load_schema,
    load_skill,
    normalize_payload,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_SKILL_PATH = REPO_ROOT / "skills" / "topic-newsletter-compiler" / "SKILL.md"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas" / "newsletter_compiler_result.json"


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


class OpenAINewsletterBackend:
    """OpenAI backend for newsletter compilation."""
    name = "openai"

    def __init__(self, tool_policy: ToolPolicy):
        self.tool_policy = tool_policy

    def run(self, skill, request: SkillRequest) -> dict:
        """Run newsletter compilation via OpenAI."""
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_NEWSLETTER_MODEL", "gpt-4o-mini")

        if not api_key:
            raise SkillRuntimeError("OPENAI_API_KEY is not set in the environment")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise SkillRuntimeError(
                "The `openai` package is required. Install it with "
                "`pip install openai`."
            ) from exc

        client = OpenAI(api_key=api_key)

        response_kwargs = {
            "model": model,
            "instructions": skill.instructions,
            "input": request.prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "newsletter_compiler_result",
                    "schema": load_schema(request.output_schema_path),
                    "strict": True,
                }
            },
        }

        response = client.responses.create(**response_kwargs)
        payload = self._extract_structured_payload(response, request)
        return payload

    def _extract_structured_payload(self, response, request: SkillRequest) -> dict:
        """Extract and validate the structured response payload."""
        raw_text = (getattr(response, "output_text", "") or "").strip()
        if not raw_text:
            raise SkillRuntimeError("OpenAI backend returned an empty response.")

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise SkillRuntimeError("OpenAI backend did not return valid structured JSON.") from exc

        schema = load_schema(request.output_schema_path)
        return normalize_payload(payload, schema=schema)


def compile_newsletter(
    research_entries: list[dict],
    skill_path: Optional[str | Path] = None,
) -> dict:
    """
    Compile a weekly newsletter from research entries using OpenAI.

    Args:
        research_entries: List of research entry dicts with keys: id, datetime, topic, content
        skill_path: Optional path to the newsletter-compiler skill file

    Returns:
        Dictionary containing compiled newsletter with keys:
        - newsletter_title
        - opening_hook
        - key_trends
        - top_highlights
        - implications
        - topics_covered
        - newsletter_markdown
        - newsletter_html (optional)

    Raises:
        SkillRuntimeError: If OpenAI is not configured or compilation fails
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

    skill_path = skill_path or DEFAULT_SKILL_PATH
    skill = load_skill(skill_path, name="topic-newsletter-compiler")
    
    backend = OpenAINewsletterBackend(ToolPolicy(enable_web_search=False))
    prompt = _build_newsletter_prompt(research_entries)
    
    result = backend.run(
        skill,
        SkillRequest(
            topic="weekly-newsletter",
            prompt=prompt,
            output_schema_path=DEFAULT_SCHEMA_PATH,
            return_response=True,
        ),
    )
    
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
