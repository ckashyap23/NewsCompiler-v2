"""
Database connection test utility - verify PostgreSQL connection works.

Usage:
    python test_database.py                    # Test with DATABASE_URL from .env
    python test_database.py postgres://...     # Test with custom URL
"""
import sys
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def test_connection(database_url: str) -> bool:
    """Test database connection and table creation."""
    try:
        from models import init_db, get_session, NewsCompilerEntry
        
        logger.info("Testing database connection...")
        logger.info(f"Database URL: {database_url[:50]}...")
        
        # Initialize database (creates tables if they don't exist)
        logger.info("Initializing database schema...")
        init_db(database_url)
        logger.info("✓ Database initialized")
        
        # Try to query
        logger.info("Testing query...")
        session = get_session(database_url)
        count = session.query(NewsCompilerEntry).count()
        session.close()
        logger.info(f"✓ Query successful. Current entries: {count}")
        
        # Try to insert a test entry
        logger.info("Testing write operation...")
        from database import store_research_result
        entry_datetime = store_research_result(
            topic="Test Topic",
            content="Test content",
            database_url=database_url
        )
        logger.info(f"Successfully stored test entry at {entry_datetime}")
        
        # Verify insert
        session = get_session(database_url)
        new_count = session.query(NewsCompilerEntry).count()
        session.close()
        logger.info(f"✓ New entry count: {new_count}")
        
        logger.info("=" * 60)
        logger.info("✓ ALL TESTS PASSED - Database is ready!")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"✗ Test failed: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test database connection and operations"
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="Database URL (uses DATABASE_URL from .env if not provided)"
    )
    
    args = parser.parse_args()
    
    # Get database URL
    if args.url:
        database_url = args.url
    else:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            logger.error("No DATABASE_URL provided and not found in .env")
            logger.info("Usage: python test_database.py <database_url>")
            logger.info("Or set DATABASE_URL in .env file")
            return 1
    
    success = test_connection(database_url)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
