"""
Orchestrator: Research a topic and email the summary to recipients.

Usage:
    python orchestrator.py recipient1@example.com recipient2@example.com
    python orchestrator.py "topic" recipient1@example.com recipient2@example.com
    python orchestrator.py --topic "topic" recipient1@example.com recipient2@example.com
    python orchestrator.py -s "Custom subject" "topic" recipient@example.com
"""
import argparse
import re
import sys
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from database import store_research_result
from models import init_db
from send_email import send_email
from topic_research import run_topic_research

DEFAULT_TOPICS_BY_DAY = {
    "Monday": "new AI tools, developer tools, SaaS products, open source releases, product launches in tech and AI in the last 7 days",
    "Tuesday": "AI research papers, machine learning breakthroughs, LLM advancements, multimodal AI developments, new models and benchmarks in the last 7 days",
    "Wednesday": "AI startup funding, venture capital investments, tech acquisitions, mergers, new startups and funding rounds in the last 7 days",
    "Thursday": "updates from major tech companies like Google, OpenAI, Microsoft, Meta, Amazon, Apple including product updates, strategy shifts and announcements in the last 7 days",
    "Friday": "AI industry trends, emerging technologies, enterprise AI adoption, automation trends, developer ecosystem trends and future predictions in the last 7 days",
    "Saturday": "opinions and perspectives from tech leaders, AI experts interviews, industry debates, future of AI discussions, risks and opportunities in the last 7 days",
    "Sunday": "AI regulation, government policies, AI ethics, data privacy, global AI policy updates and societal impact of AI in the last 7 days"
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_topic_for_today() -> str:
    """Return the default topic prompt for the current UTC weekday."""
    day = datetime.utcnow().strftime("%A")
    return DEFAULT_TOPICS_BY_DAY.get(day, DEFAULT_TOPICS_BY_DAY["Monday"])


def resolve_topic(topic: Optional[str] = None) -> str:
    """Use the provided topic, or fall back to the weekday-based default."""
    if topic and topic.strip():
        return topic.strip()
    return get_topic_for_today()


def _looks_like_email(value: str) -> bool:
    """Best-effort check used to disambiguate CLI arguments."""
    return bool(EMAIL_PATTERN.match(value.strip()))


def run(
    topic: Optional[str],
    recipients: list[str],
    subject: Optional[str] = None,
    store_to_db: bool = True,
) -> str:
    """
    Run topic research and email the summary to the given recipients.

    Args:
        topic: The research topic. If omitted, the weekday-based default is used.
        recipients: List of recipient email addresses.
        subject: Optional email subject. Defaults to "Topic Research: {topic}".

    Returns:
        The research summary text that was emailed.
    """
    resolved_topic = resolve_topic(topic)
    summary = run_topic_research(resolved_topic)
    email_subject = subject or f"Topic Research: {resolved_topic}"
    send_email(summary, recipients, subject=email_subject)

    if store_to_db:
        store_research_result(email_subject, summary)

    return summary


def parse_cli_inputs(
    inputs: list[str],
    explicit_topic: Optional[str] = None,
) -> tuple[Optional[str], list[str]]:
    """
    Parse CLI inputs while supporting both legacy and no-topic invocation styles.
    """
    if explicit_topic is not None:
        return explicit_topic, inputs

    if not inputs:
        raise ValueError("at least one recipient email address is required")

    if _looks_like_email(inputs[0]):
        return None, inputs

    if len(inputs) < 2:
        raise ValueError(
            "when passing a topic positionally, include at least one recipient email address"
        )

    return inputs[0], inputs[1:]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Research a topic and email the summary to recipients"
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help='Recipients, or "topic recipients..." when using the legacy positional form',
    )
    parser.add_argument(
        "-t",
        "--topic",
        default=None,
        help="Optional research topic. If omitted, a weekday-based default is used.",
    )
    parser.add_argument(
        "-s",
        "--subject",
        default=None,
        help="Email subject (default: Topic Research: <topic>)",
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Create database tables and exit.",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip database storage for this run.",
    )
    args = parser.parse_args()

    try:
        if args.init_db:
            init_db()
            print("Database initialised.")
            return 0

        topic, recipients = parse_cli_inputs(args.inputs, explicit_topic=args.topic)
        resolved_topic = resolve_topic(topic)
        run(topic, recipients, subject=args.subject, store_to_db=not args.no_db)
        print(f"Using topic: {resolved_topic}")
        print("Research completed and email sent successfully.")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
