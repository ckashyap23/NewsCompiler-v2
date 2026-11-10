"""HTTP entry points for Railway. Work completes before the response is returned."""
import logging
import os
import secrets
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from shared.paths import ENV_PATH

load_dotenv(dotenv_path=ENV_PATH)

from daily.orchestrator import run_daily
from weekly.digest import generate_weekly_digest

logger = logging.getLogger(__name__)
app = FastAPI(title="News Compiler", version="2.0.0")
bearer = HTTPBearer(auto_error=False)


def authenticate(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    expected = (os.getenv("BACKEND_API_TOKEN") or "").strip()
    if not expected:
        raise HTTPException(503, "BACKEND_API_TOKEN is not configured")
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), expected.encode()
    ):
        raise HTTPException(401, "Invalid bearer token", headers={"WWW-Authenticate": "Bearer"})


class DailyRequest(BaseModel):
    topic: str | None = Field(default=None, max_length=2000)
    email: bool = True
    whatsapp: bool = True


class WeeklyRequest(BaseModel):
    days: int | None = Field(default=None, ge=1, le=365)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/daily-news", dependencies=[Depends(authenticate)])
def daily_news(request: DailyRequest | None = None) -> dict:
    options = request or DailyRequest()
    try:
        result = run_daily(
            topic=options.topic or os.getenv("RESEARCH_TOPIC") or None,
            email_enabled=options.email,
            whatsapp_enabled=options.whatsapp,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except Exception:
        logger.exception("Daily news failed")
        raise HTTPException(502, "Daily news failed; check server logs before retrying") from None
    delivery_failed = "failed_or_unconfirmed" in result.get("deliveries", {}).values()
    return {"status": "completed_with_delivery_errors" if delivery_failed else "completed", **result}


@app.post("/weekly-digest", dependencies=[Depends(authenticate)])
def weekly_digest(request: WeeklyRequest | None = None) -> dict:
    try:
        days = request.days if request and request.days is not None else int(os.getenv("WEEKLY_DIGEST_DAYS", "7"))
        if not 1 <= days <= 365:
            raise ValueError("WEEKLY_DIGEST_DAYS must be between 1 and 365")
        # Weekly HTTP publishing goes to LinkedIn; daily recipient settings do not add email here.
        result = generate_weekly_digest(days=days, no_email=True)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except Exception:
        logger.exception("Weekly digest failed")
        raise HTTPException(502, "Weekly digest failed; check server logs before retrying") from None
    if result is None:
        return {"status": "skipped", "reason": "No research entries found"}
    return {"status": "completed", "linkedin": "published", "newsletter": result}
