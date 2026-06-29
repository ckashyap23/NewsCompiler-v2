"""
Weekly digest generator: collects recent research data and creates a LinkedIn post.

Uses the "topic-newsletter-compiler" skill with OpenAI to analyze data.

Usage:
    python weekly_digest.py                    # Compile and post digest
    python weekly_digest.py --dry-run          # Preview without posting
    python weekly_digest.py --days 14          # Use last 14 days instead
    python weekly_digest.py --no-post          # Compile but don't post to LinkedIn

Requires LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN for LinkedIn posting.
"""
import argparse
import logging
import os
from collections import Counter
from datetime import datetime
from typing import Optional

from database import get_recent_entries_by_calendar_days
from linkedin_connector import post_to_linkedin
from newsletter_compiler import compile_newsletter
from send_email import send_email


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _build_fallback_newsletter(entries_data: list[dict]) -> dict:
    """Build a simple local newsletter when OpenAI compilation is unavailable."""
    topics = [str(entry.get("topic", "")).strip() for entry in entries_data if entry.get("topic")]
    topic_counts = Counter(topics)
    top_topics = [topic for topic, _ in topic_counts.most_common(5)]

    highlights = []
    for entry in entries_data[:5]:
        topic = entry.get("topic", "Unknown topic")
        content = str(entry.get("content", "")).strip()
        snippet = (content[:180] + "...") if len(content) > 180 else content
        highlights.append(f"{topic}: {snippet}")

    title = f"Weekly Industry Pulse - {datetime.utcnow().strftime('%Y-%m-%d')}"
    hook = "Here are the most relevant updates from this week's tracked topics."
    implications = (
        "Near-term signal: organizations continue balancing AI adoption, cost control, "
        "and operational resilience."
    )

    markdown_lines = [
        f"## {title}",
        "",
        hook,
        "",
        "### Key Trends",
    ]
    markdown_lines.extend([f"- {topic}" for topic in (top_topics or ["No dominant trend detected"])])
    markdown_lines.append("")
    markdown_lines.append("### Top Highlights")
    markdown_lines.extend([f"- {item}" for item in (highlights or ["No highlights available"])])
    markdown_lines.append("")
    markdown_lines.append("### Implications")
    markdown_lines.append(implications)

    return {
        "newsletter_title": title,
        "opening_hook": hook,
        "key_trends": top_topics or ["No dominant trend detected"],
        "top_highlights": highlights or ["No highlights available"],
        "implications": implications,
        "topics_covered": list(topic_counts.keys()),
        "newsletter_markdown": "\n".join(markdown_lines),
    }


def generate_weekly_digest(
    days: int = 7,
    recipients: Optional[list[str]] = None,
    dry_run: bool = False,
    no_post: bool = False,
    no_email: bool = False,
) -> Optional[dict]:
    """
    Generate a weekly digest from stored research entries using OpenAI.
    
    Args:
        days: Number of days to look back (default 7).
        recipients: Optional email recipients for the compiled digest.
        dry_run: If True, don't post to LinkedIn, just return the content.
        no_post: If True, don't post to LinkedIn.
        no_email: If True, don't email the digest.
    
    Returns:
        The compiled newsletter dict with keys: newsletter_title, opening_hook,
        key_trends, top_highlights, implications, topics_covered, newsletter_markdown.
        Returns None if no entries found.
    
    Raises:
        Exception: If OpenAI configuration is missing or compilation fails.
    """
    logger.info(f"Fetching research entries from last {days} calendar day(s)...")

    entries = get_recent_entries_by_calendar_days(days=days)

    if not entries:
        logger.warning(f"No research entries found in the last {days} days.")
        return None

    logger.info(f"Found {len(entries)} entries. Compiling newsletter with OpenAI...")

    entries_data = []
    for entry in entries:
        entries_data.append({
            "datetime": entry.datetime.isoformat() if hasattr(entry.datetime, 'isoformat') else str(entry.datetime),
            "topic": entry.topic,
            "content": entry.content,
        })

    try:
        newsletter = compile_newsletter(entries_data)
    except Exception as e:
        if dry_run or no_post:
            logger.warning(
                "OpenAI compilation unavailable (%s). Using local fallback newsletter for preview.",
                e,
            )
            newsletter = _build_fallback_newsletter(entries_data)
        else:
            logger.error(f"Failed to compile newsletter: {e}", exc_info=True)
            raise

    logger.info("=" * 60)
    logger.info("WEEKLY NEWSLETTER")
    logger.info("=" * 60)
    logger.info(f"Title: {newsletter.get('newsletter_title', 'N/A')}")
    logger.info(f"Hook: {newsletter.get('opening_hook', 'N/A')}")
    logger.info("=" * 60)
    logger.info(newsletter.get("newsletter_markdown", "No content"))
    logger.info("=" * 60)

    if dry_run:
        logger.info("DRY RUN: Not posting to LinkedIn.")
        return newsletter

    if no_post:
        logger.info("NO_POST: Newsletter compiled but not posted to LinkedIn.")
    else:
        # Post to LinkedIn
        logger.info("Posting to LinkedIn...")
        newsletter_content = newsletter.get("newsletter_markdown", "")
        success = post_to_linkedin(
            content=newsletter_content,
            title=newsletter.get("newsletter_title", "Weekly News Digest")
        )

        if success:
            logger.info("Successfully posted to LinkedIn.")
        else:
            logger.error("Failed to post to LinkedIn.")

    effective_recipients = recipients or [r for r in os.getenv("RECIPIENT_EMAILS", "").split() if r]
    if effective_recipients and not no_email:
        logger.info("Sending weekly digest email to %d recipient(s)...", len(effective_recipients))
        send_email(
            newsletter.get("newsletter_markdown", ""),
            effective_recipients,
            subject=newsletter.get("newsletter_title", "Weekly News Digest"),
        )
        logger.info("Weekly digest email sent.")
    elif no_email:
        logger.info("NO_EMAIL: Newsletter compiled but not emailed.")

    return newsletter


def main():
    default_days = int(os.getenv("WEEKLY_DIGEST_DAYS", "7"))

    parser = argparse.ArgumentParser(
        description="Generate and post weekly news digest to LinkedIn"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=default_days,
        help="Number of calendar days to look back (default: WEEKLY_DIGEST_DAYS or 7)"
    )
    parser.add_argument(
        "recipients",
        nargs="*",
        help="Optional recipient email addresses for the weekly digest email"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview digest without posting to LinkedIn"
    )
    parser.add_argument(
        "--no-post",
        action="store_true",
        help="Compile digest but don't post to LinkedIn"
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Compile digest but don't email recipients"
    )
    
    args = parser.parse_args()
    
    try:
        result = generate_weekly_digest(
            days=args.days,
            recipients=args.recipients,
            dry_run=args.dry_run,
            no_post=args.no_post,
            no_email=args.no_email,
        )
        if result:
            return 0
        else:
            return 1
    except Exception as e:
        logger.error(f"Error generating digest: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
