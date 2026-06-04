"""
Send email via Gmail SMTP to a list of recipients.

Usage:
    python send_email.py "Your message text" recipient1@example.com recipient2@example.com
    python send_email.py -s "Subject" "Your message text" recipient@example.com

Sender email is read from GMAIL_EMAIL in .env.
Password (Gmail App Password) is read from GMAIL_APP_PASSWORD in .env.
"""
import argparse
import os
import smtplib
import socket
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
GMAIL_SMTP_SSL_PORT = 465
DEFAULT_TIMEOUT_SECONDS = 20

ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)


def _clean_env_value(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        value = value[1:-1]
    if name == "GMAIL_APP_PASSWORD":
        value = value.replace(" ", "")
    return value.strip()


def _build_message(sender: str, recipients: list[str], subject: str, text: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(text)
    return msg


def _send_via_starttls(email: str, password: str, recipients: list[str], msg: EmailMessage) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=DEFAULT_TIMEOUT_SECONDS) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(email, password)
        smtp.send_message(msg, from_addr=email, to_addrs=recipients)


def _send_via_ssl(email: str, password: str, recipients: list[str], msg: EmailMessage) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(
        GMAIL_SMTP_HOST,
        GMAIL_SMTP_SSL_PORT,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        context=context,
    ) as smtp:
        smtp.login(email, password)
        smtp.send_message(msg, from_addr=email, to_addrs=recipients)


def _raise_helpful_smtp_error(exc: Exception) -> None:
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        raise RuntimeError(
            "Gmail rejected the login. Confirm 2-Step Verification is enabled and "
            "use a Gmail App Password in GMAIL_APP_PASSWORD, not your regular password."
        ) from exc
    if isinstance(exc, (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, socket.timeout, TimeoutError)):
        raise RuntimeError(
            "Could not connect to Gmail SMTP. Check internet access, firewall/VPN rules, "
            "or whether your network blocks ports 587/465."
        ) from exc
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        raise RuntimeError("Gmail refused one or more recipient addresses.") from exc
    if isinstance(exc, smtplib.SMTPException):
        raise RuntimeError(f"Gmail SMTP error: {exc}") from exc
    raise


def send_email(
    text: str,
    recipients: list[str],
    subject: str = "Message",
) -> None:
    """Send an email via Gmail to the given recipients."""
    email = _clean_env_value("GMAIL_EMAIL")
    password = _clean_env_value("GMAIL_APP_PASSWORD")

    if not email:
        raise RuntimeError("GMAIL_EMAIL is not set in .env")
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD is not set in .env")
    if not recipients:
        raise ValueError("At least one recipient is required")

    msg = _build_message(email, recipients, subject, text)

    try:
        _send_via_starttls(email, password, recipients, msg)
    except Exception as starttls_exc:
        try:
            _send_via_ssl(email, password, recipients, msg)
        except Exception as ssl_exc:
            preferred_exc = ssl_exc if isinstance(ssl_exc, smtplib.SMTPException) else starttls_exc
            _raise_helpful_smtp_error(preferred_exc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send email via Gmail to a list of recipients"
    )
    parser.add_argument("text", help="The email body text")
    parser.add_argument("recipients", nargs="+", help="One or more recipient email addresses")
    parser.add_argument("-s", "--subject", default="Message", help="Email subject (default: Message)")
    args = parser.parse_args()

    try:
        send_email(args.text, args.recipients, subject=args.subject)
        print(f"Email sent to {len(args.recipients)} recipient(s).")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
