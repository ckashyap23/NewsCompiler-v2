"""
Database operations for news compiler.
"""
from datetime import datetime, timedelta, timezone
from models import NewsCompilerEntry, get_session, init_db


def store_research_result(
    topic: str,
    content: str,
    database_url: str | None = None,
) -> datetime:
    """
    Store a research result in the database.

    Args:
        topic: The research topic.
        content: The research summary/content.
        database_url: Optional database URL override.

    Returns:
        The datetime of the stored entry.
    """
    # Ensure the target table exists before the first insert.
    init_db(database_url)
    session = get_session(database_url)
    try:
        entry = NewsCompilerEntry(
            topic=topic,
            content=content,
        )
        session.add(entry)
        session.commit()
        entry_datetime = entry.datetime
        return entry_datetime
    finally:
        session.close()


def get_recent_entries(
    days: int = 7,
    database_url: str | None = None,
) -> list[NewsCompilerEntry]:
    """
    Get research entries from the last N days.

    Args:
        days: Number of days to look back (default 7).
        database_url: Optional database URL override.

    Returns:
        List of NewsCompilerEntry objects.
    """
    session = get_session(database_url)
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        entries = session.query(NewsCompilerEntry).filter(
            NewsCompilerEntry.datetime >= cutoff_date
        ).order_by(NewsCompilerEntry.datetime.desc()).all()
        # Convert to detached objects before closing session
        session.expunge_all()
        return entries
    finally:
        session.close()


def get_recent_entries_by_calendar_days(
    days: int = 7,
    database_url: str | None = None,
) -> list[NewsCompilerEntry]:
    """
    Get entries from the current UTC day and the previous N-1 full UTC days.

    Example:
        days=7 on a Thursday returns data from Friday 00:00:00 UTC through now.
    """
    if days <= 0:
        return []

    session = get_session(database_url)
    try:
        now_utc = datetime.now(timezone.utc)
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        cutoff_date = today_start - timedelta(days=days - 1)
        entries = session.query(NewsCompilerEntry).filter(
            NewsCompilerEntry.datetime >= cutoff_date
        ).order_by(NewsCompilerEntry.datetime.desc()).all()
        session.expunge_all()
        return entries
    finally:
        session.close()


def get_all_entries(database_url: str | None = None) -> list[NewsCompilerEntry]:
    """
    Get all research entries.

    Args:
        database_url: Optional database URL override.

    Returns:
        List of all NewsCompilerEntry objects.
    """
    session = get_session(database_url)
    try:
        entries = session.query(NewsCompilerEntry).order_by(
            NewsCompilerEntry.datetime.desc()
        ).all()
        session.expunge_all()
        return entries
    finally:
        session.close()
