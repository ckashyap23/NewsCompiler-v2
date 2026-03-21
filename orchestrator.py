"""
Orchestrator: Research a topic and email the summary to recipients.

Usage:
    python orchestrator.py "topic" recipient1@example.com recipient2@example.com
    python orchestrator.py -s "Custom subject" "topic" recipient@example.com
"""
import argparse
import sys
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from send_email import send_email
from topic_research import run_topic_research


def run(
    topic: str,
    recipients: list[str],
    subject: Optional[str] = None,
) -> str:
    """
    Run topic research and email the summary to the given recipients.

    Args:
        topic: The research topic.
        recipients: List of recipient email addresses.
        subject: Optional email subject. Defaults to "Topic Research: {topic}".

    Returns:
        The research summary text that was emailed.
    """
    summary = run_topic_research(topic)
    email_subject = subject or f"Topic Research: {topic}"
    send_email(summary, recipients, subject=email_subject)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Research a topic and email the summary to recipients"
    )
    parser.add_argument("topic", help="The research topic")
    parser.add_argument(
        "recipients",
        nargs="+",
        help="One or more recipient email addresses",
    )
    parser.add_argument(
        "-s",
        "--subject",
        default=None,
        help="Email subject (default: Topic Research: <topic>)",
    )
    args = parser.parse_args()

    try:
        run(args.topic, args.recipients, subject=args.subject)
        print("Research completed and email sent successfully.")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
