"""
Orchestrator: Research a topic, archive it, and deliver it to email and WhatsApp.

Usage:
    python -m daily.orchestrator
    python -m daily.orchestrator recipient1@example.com recipient2@example.com
    python -m daily.orchestrator "topic" recipient@example.com
    python -m daily.orchestrator --topic "topic" recipient@example.com
"""
import argparse
import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

from shared.paths import ENV_PATH

load_dotenv(dotenv_path=ENV_PATH)

from shared.database import init_db, store_research_result
from shared.send_email import send_email
from daily.topic_research import run_topic_research
from daily.whatsapp_connector import get_phone_recipients, get_relay_config, send_whatsapp

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
logger = logging.getLogger(__name__)


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
    return run_daily(topic, recipients, subject=subject, store_to_db=store_to_db)["content"]


class DailyDeliveryError(RuntimeError):
    """One or more channels failed; other channels may already have delivered."""

    def __init__(self, result: dict):
        super().__init__("Daily news generated, but one or more deliveries failed")
        self.result = result


def run_daily(
    topic: Optional[str] = None,
    recipients: Optional[list[str]] = None,
    subject: Optional[str] = None,
    store_to_db: bool = True,
    email_enabled: bool = True,
    whatsapp_enabled: bool = True,
) -> dict:
    """Generate once, archive the content, then attempt each configured channel."""
    emails = (os.getenv("RECIPIENT_EMAILS") or "").split() if recipients is None else recipients
    emails = emails if email_enabled else []
    phones = get_phone_recipients() if whatsapp_enabled else []
    if not emails and not phones:
        raise ValueError("Configure RECIPIENT_EMAILS and/or RECEIPENT_PHONE_NUMBERS for an enabled channel")
    if phones:
        get_relay_config()  # Fail before generating content if relay settings are missing.

    resolved_topic = resolve_topic(topic)
    summary = run_topic_research(resolved_topic)
    if not summary or not summary.strip():
        raise RuntimeError("Research returned empty content")
    email_subject = subject or f"Topic Research: {resolved_topic}"
    stored_at = store_research_result(email_subject, summary) if store_to_db else None
    result = {
        "topic": resolved_topic,
        "subject": email_subject,
        "content": summary,
        "stored_at": stored_at.isoformat() if stored_at else None,
        "deliveries": {"email": "skipped", "whatsapp": "skipped"},
    }
    for channel, targets in (("email", emails), ("whatsapp", phones)):
        if not targets:
            continue
        try:
            if channel == "email":
                send_email(summary, targets, subject=email_subject)
            else:
                send_whatsapp(summary, targets)
            # A relay 2xx confirms acceptance, not delivery to recipients' devices.
            result["deliveries"][channel] = "sent" if channel == "email" else "accepted"
        except Exception:
            logger.exception("Daily %s delivery failed or is unconfirmed", channel)
            result["deliveries"][channel] = "failed_or_unconfirmed"
    if "failed_or_unconfirmed" in result["deliveries"].values():
        raise DailyDeliveryError(result)
    return result


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
        description="Research a topic and deliver it to configured email and WhatsApp recipients"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
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

        inputs = args.inputs or [
            value for value in os.getenv("RECIPIENT_EMAILS", "").split() if value
        ]
        configured_topic = args.topic
        if configured_topic is None:
            configured_topic = os.getenv("RESEARCH_TOPIC") or None

        if not inputs and get_phone_recipients():
            topic, recipients = configured_topic, []
        else:
            topic, recipients = parse_cli_inputs(inputs, explicit_topic=configured_topic)
        resolved_topic = resolve_topic(topic)
        run(topic, recipients, subject=args.subject, store_to_db=not args.no_db)
        print(f"Using topic: {resolved_topic}")
        print("Research completed and configured deliveries accepted successfully.")
        return 0
    except DailyDeliveryError as exc:
        print(f"Error: {exc}. Delivery results: {exc.result['deliveries']}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
