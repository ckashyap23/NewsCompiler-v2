from pathlib import Path
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

DEFAULT_SKILL_PATH = Path(
    r"C:\Users\kgtec\.codex\skills\topic-research-summarizer\SKILL.md"
)


def run_topic_research(
    topic,
    model="gpt-5",
    skill_path=DEFAULT_SKILL_PATH,
    return_response=False,
):
    """
    Run the installed Codex research skill through the OpenAI Responses API.

    Args:
        topic (str): The research topic or prompt.
        model (str, optional): OpenAI model name. Defaults to "gpt-5".
        skill_path (str | Path, optional): Path to the installed skill file.
        return_response (bool, optional): Return the raw SDK response as well.

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

    response = client.responses.create(
        model=model,
        instructions=skill_instructions,
        tools=[{"type": "web_search"}],
        include=["web_search_call.action.sources"],
        input=(
            "Research the following topic, keep only the most relevant "
            "results, and return a concise sourced summary.\n\n"
            f"{topic}"
        ),
    )

    text = (getattr(response, "output_text", "") or "").strip()

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
