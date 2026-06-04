"""
SQLAlchemy models for news compiler database.
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()


class NewsCompilerEntry(Base):
    """Model for storing research results."""
    __tablename__ = "news_compiler_db"

    datetime = Column(DateTime, default=datetime.utcnow, primary_key=True, nullable=False, index=True)
    topic = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)

    def __repr__(self):
        return (
            f"<NewsCompilerEntry("
            f"datetime={self.datetime}, "
            f"topic={self.topic[:50]}..."
            f")>"
        )


def get_database_url() -> str:
    """Get database URL from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Format: postgresql://user:password@host:port/dbname"
        )
    return db_url


def init_db(database_url: str | None = None) -> None:
    """Initialize database and create tables."""
    url = database_url or get_database_url()
    engine = create_engine(url)
    Base.metadata.create_all(engine)


def get_session(database_url: str | None = None):
    """Get a database session."""
    url = database_url or get_database_url()
    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    return Session()
