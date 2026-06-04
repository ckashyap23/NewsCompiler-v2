from pathlib import Path
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, OpenAI

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SKILL_PATH = BASE_DIR / "skills" / "topic-research-summarizer" / "SKILL.md"


def run_topic_research(
    topic: str,
    model: str = "gpt-4o",
    skill_path: Path = DEFAULT_SKILL_PATH,
    return_response: bool = False,
    log_progress: bool = False,
) -> str:
    """Research a topic via OpenAI Responses API with web search."""
    if not topic or not str(topic).strip():
        raise ValueError("topic is required")

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in the environment")

    skill_file = Path(skill_path)
    if not skill_file.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_file}")

    skill_instructions = skill_file.read_text(encoding="utf-8")
    client = OpenAI()
    started_at = time.monotonic()
    today_utc = datetime.now(timezone.utc).date().isoformat()

    if log_progress:
        print(f"Starting research for topic: {topic}", file=sys.stderr)

    try:
        response = client.responses.create(
            model=model,
            instructions=skill_instructions,
            tools=[{"type": "web_search_preview"}],
            input=(
                "Research the following topic and return a concise sourced summary.\n"
                "This is a one-shot automated newsletter workflow — do not ask clarifying questions.\n"
                "Make reasonable assumptions when details are ambiguous and continue.\n"
                "Prefer official and primary sources; add strong secondary reporting for context.\n"
                f"Assume today's UTC date is {today_utc}.\n\n"
                "Topic:\n"
                f"{topic}"
            ),
        )
    except APIConnectionError as exc:
        elapsed = time.monotonic() - started_at
        raise RuntimeError(
            f"Research request failed due to a connection issue after {elapsed:.1f}s."
        ) from exc
    except APIStatusError as exc:
        elapsed = time.monotonic() - started_at
        raise RuntimeError(
            f"Research request failed with API status {exc.status_code} after {elapsed:.1f}s."
        ) from exc

    text = (getattr(response, "output_text", "") or "").strip()
    elapsed = time.monotonic() - started_at

    if log_progress:
        print(f"Research completed in {elapsed:.1f}s.", file=sys.stderr)

    if return_response:
        return text, response
    return text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python topic_research.py <topic>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    try:
        print(run_topic_research(query))
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
