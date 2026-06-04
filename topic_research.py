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
    topic,
    model="gpt-5",
    skill_path=DEFAULT_SKILL_PATH,
    return_response=False,
    log_progress=False,
):
    """
    Run the installed Codex research skill through the OpenAI Responses API.

    Args:
        topic (str): The research topic or prompt.
        model (str, optional): OpenAI model name. Defaults to "gpt-5".
        skill_path (str | Path, optional): Path to the installed skill file.
        return_response (bool, optional): Return the raw SDK response as well.
        log_progress (bool, optional): Print start/finish timing messages.

    Returns:
        str | tuple[str, object]: The summary text, or (text, response) when
        return_response is True.
    """
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
        print(f"Using model {model}. Waiting for the API response...", file=sys.stderr)

    try:
        response = client.responses.create(
            model=model,
            instructions=skill_instructions,
            tools=[{"type": "web_search"}],
            include=["web_search_call.action.sources"],
            input=(
                "Research the following topic and return a concise sourced summary.\n"
                "This is a one-shot automated newsletter workflow, so do not ask "
                "clarifying questions.\n"
                "When details are ambiguous, make the best reasonable assumptions "
                "and continue.\n"
                "Prefer official and primary sources first, but include strong "
                "secondary reporting when it helps confirm or contextualize a "
                "development.\n"
                f"Assume today's UTC date is {today_utc}. Resolve any relative "
                "time window such as 'last 7 days' using that date.\n"
                "If evidence is incomplete, say so briefly, but still provide the "
                "best useful answer you can.\n\n"
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
            f"Research request failed with API status {exc.status_code} "
            f"after {elapsed:.1f}s."
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
        print(run_topic_research(query, log_progress=True))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
