"""Send daily research to the configured WhatsApp relay."""
import os
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv
from shared.paths import ENV_PATH

load_dotenv(dotenv_path=ENV_PATH)


def get_phone_recipients() -> list[str]:
    # Keep the spelling of the environment variable used by the existing relay setup.
    return (os.getenv("RECEIPENT_PHONE_NUMBERS") or "").split()


def get_relay_config() -> tuple[str, str]:
    base = (os.getenv("API_PATH") or "").strip().rstrip("/")
    path = (os.getenv("API_POST_PATH") or "").strip()
    token = (os.getenv("BEARER_TOKEN") or "").strip()
    if not base or not path or not token:
        raise ValueError("WhatsApp requires API_PATH, API_POST_PATH, and BEARER_TOKEN")
    if urlsplit(base).scheme != "https" or not urlsplit(base).netloc:
        raise ValueError("API_PATH must be an HTTPS URL")
    if not path.startswith("/") or path.startswith("//") or urlsplit(path).netloc:
        raise ValueError("API_POST_PATH must be a relative path starting with /")
    return base + path, token


def send_whatsapp(message: str, recipients: list[str]) -> None:
    if not message.strip():
        raise ValueError("WhatsApp message cannot be empty")
    if not recipients:
        raise ValueError("At least one WhatsApp recipient is required")
    url, token = get_relay_config()
    try:
        # Do not automatically retry a POST: the relay may already have sent it.
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"recipients": recipients, "message": message},
            timeout=(10, 60),
            allow_redirects=False,
        )
    except requests.RequestException:
        raise RuntimeError("WhatsApp relay could not be reached; delivery is unconfirmed") from None
    if not 200 <= response.status_code < 300:
        # Response bodies can contain recipient data or credentials.
        raise RuntimeError(f"WhatsApp relay returned HTTP {response.status_code}")
