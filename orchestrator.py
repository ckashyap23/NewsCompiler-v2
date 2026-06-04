"""
Orchestrator: research a topic, email the summary, and store it in the database.

Usage:
    python orchestrator.py recipient1@example.com recipient2@example.com
    python orchestrator.py "topic" recipient1@example.com recipient2@example.com
    python orchestrator.py --topic "topic" recipient1@example.com recipient2@example.com
    python orchestrator.py -s "Custom subject" "topic" recipient@example.com

Render cron usage:
    RESEARCH_TOPIC=...
    RECIPIENT_EMAILS=email1@example.com email2@example.com
    python orchestrator.py
"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

from database import store_research_result
from models import init_db
from send_email import send_email
from topic_research import run_topic_research

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_TOPICS_BY_DAY = {
    "Monday": "new AI tools, developer tools, SaaS products, open source releases, product launches in tech and AI in the last 7 days",
    "Tuesday": "AI research papers, machine learning breakthroughs, LLM advancements, multimodal AI developments, new models and benchmarks in the last 7 days",
    "Wednesday": "AI startup funding, venture capital investments, tech acquisitions, mergers, new startups and funding rounds in the last 7 days",
    "Thursday": "updates from major tech companies like Google, OpenAI, Microsoft, Meta, Amazon, Apple including product updates, strategy shifts and announcements in the last 7 days",
    "Friday": "AI industry trends, emerging technologies, enterprise AI adoption, automation trends, developer ecosystem trends and future predictions in the last 7 days",
    "Saturday": "opinions and perspectives from tech leaders, AI expert interviews, industry debates, future of AI discussions, risks and opportunities in the last 7 days",
    "Sunday": "AI regulation, government policies, AI ethics, data privacy, global AI policy updates and societal impact of AI in the last 7 days",
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_topic_for_today() -> str:
    """Return the default research topic for the current UTC weekday."""
    day = datetime.utcnow().strftime("%A")
    return DEFAULT_TOPICS_BY_DAY.get(day, DEFAULT_TOPICS_BY_DAY["Monday"])


def resolve_topic(topic: Optional[str] = None) -> str:
    """Use the provided topic, else RESEARCH_TOPIC, else weekday default."""
    if topic and topic.strip():
        return topic.strip()

    env_topic = (os.getenv("RESEARCH_TOPIC") or "").strip()
    if env_topic:
        return env_topic

    return get_topic_for_today()


def _looks_like_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.match(value.strip()))


def parse_cli_inputs(
    inputs: list[str],
    explicit_topic: Optional[str] = None,
) -> tuple[Optional[str], list[str]]:
    """Support both `topic recipients...` and `recipients...` invocation styles."""
    if explicit_topic is not None:
        return explicit_topic, inputs

    if not inputs:
        return None, []

    if _looks_like_email(inputs[0]):
        return None, inputs

    if len(inputs) < 2:
        raise ValueError(
            "when passing a topic positionally, include at least one recipient email address"
        )

    return inputs[0], inputs[1:]


def run(
    topic: Optional[str],
    recipients: list[str],
    subject: Optional[str] = None,
    store_to_db: bool = True,
) -> str:
    """Research topic, send email, and optionally store the sent content in the DB."""
    resolved_topic = resolve_topic(topic)
    summary = run_topic_research(resolved_topic, log_progress=True)
    email_subject = subject or f"Topic Research: {resolved_topic}"

    send_email(summary, recipients, subject=email_subject)
    logger.info("Email sent to %d recipient(s).", len(recipients))

    if store_to_db:
        try:
            entry_datetime = store_research_result(email_subject, summary)
            logger.info("Stored research email in database at %s.", entry_datetime)
        except Exception as exc:
            logger.warning("Failed to store research result in database: %s", exc)

    return summary


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Research a topic, email the summary, and store it in the database"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Recipients, or 'topic recipients...' when using the positional topic form",
    )
    parser.add_argument(
        "-t",
        "--topic",
        default=None,
        help="Optional research topic. If omitted, uses RESEARCH_TOPIC or weekday rotation.",
    )
    parser.add_argument(
        "-s",
        "--subject",
        default=None,
        help="Email subject. Defaults to 'Topic Research: <resolved topic>'.",
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

    if args.init_db:
        init_db()
        print("Database initialised.")
        return 0

    try:
        topic, recipients = parse_cli_inputs(args.inputs, explicit_topic=args.topic)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not recipients:
        recipients = [r for r in (os.getenv("RECIPIENT_EMAILS") or "").split() if r]

    if not recipients:
        print(
            "Error: at least one recipient is required (CLI or RECIPIENT_EMAILS env var)",
            file=sys.stderr,
        )
        return 1

    try:
        resolved_topic = resolve_topic(topic)
        run(topic, recipients, subject=args.subject, store_to_db=not args.no_db)
        print(f"Using topic: {resolved_topic}")
        print("Research completed and email sent successfully.")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        logger.error("Fatal orchestrator error", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
