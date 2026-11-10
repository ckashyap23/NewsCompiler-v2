"""
Send email via Gmail SMTP or the Resend HTTPS API to a list of recipients.

Usage:
    python -m shared.send_email "Your message text" recipient1@example.com recipient2@example.com
    python -m shared.send_email -s "Subject" "Your message text" recipient@example.com

Sender email is read from GMAIL_EMAIL in .env.
Password (Gmail App Password) is read from GMAIL_APP_PASSWORD in .env.
Set EMAIL_PROVIDER=resend, RESEND_API_KEY and EMAIL_FROM to use HTTPS instead.
"""
import os
import ssl
import sys
import argparse
import smtplib
from email.message import EmailMessage

import requests
from dotenv import load_dotenv
from shared.paths import ENV_PATH

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
GMAIL_SMTP_SSL_PORT = 465
DEFAULT_TIMEOUT_SECONDS = 20

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
        refused = smtp.send_message(msg, from_addr=email, to_addrs=recipients)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def _send_via_ssl(email: str, password: str, recipients: list[str], msg: EmailMessage) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(
        GMAIL_SMTP_HOST,
        GMAIL_SMTP_SSL_PORT,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        context=context,
    ) as smtp:
        smtp.login(email, password)
        refused = smtp.send_message(msg, from_addr=email, to_addrs=recipients)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def _raise_helpful_smtp_error(exc: Exception) -> None:
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        raise RuntimeError(
            "Gmail rejected the login. Confirm 2-Step Verification is enabled and "
            "use a Gmail App Password in GMAIL_APP_PASSWORD, not your regular password."
        ) from exc
    if isinstance(exc, (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected)) or (
        isinstance(exc, OSError) and not isinstance(exc, smtplib.SMTPException)
    ):
        raise RuntimeError(
            "Could not connect to Gmail SMTP. Check internet access, firewall/VPN rules, "
            "or whether your network blocks ports 587/465. Railway requires Pro or above "
            "for SMTP; redeploy after upgrading, or use EMAIL_PROVIDER=resend with "
            "RESEND_API_KEY and EMAIL_FROM for HTTPS delivery."
        ) from exc
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        raise RuntimeError("Gmail refused one or more recipient addresses.") from exc
    if isinstance(exc, smtplib.SMTPException):
        raise RuntimeError(f"Gmail SMTP error: {exc}") from exc
    raise exc


def _send_via_resend(text: str, recipients: list[str], subject: str) -> None:
    api_key = _clean_env_value("RESEND_API_KEY")
    sender = _clean_env_value("EMAIL_FROM")
    if not api_key or not sender:
        raise RuntimeError("Resend requires RESEND_API_KEY and EMAIL_FROM (a verified sender)")
    try:
        # Never retry or fall back to SMTP after an unconfirmed POST.
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"from": sender, "to": recipients, "subject": subject, "text": text},
            timeout=(10, DEFAULT_TIMEOUT_SECONDS),
            allow_redirects=False,
        )
    except requests.RequestException:
        raise RuntimeError("Resend could not be reached; email delivery is unconfirmed") from None
    if not 200 <= response.status_code < 300:
        # Avoid leaking message content, addresses or credentials in provider errors.
        raise RuntimeError(
            f"Resend returned HTTP {response.status_code}. Check the API key, "
            "verified EMAIL_FROM sender, and account recipient restrictions."
        )
    try:
        result = response.json()
    except ValueError:
        result = None
    if not isinstance(result, dict) or not result.get("id"):
        raise RuntimeError("Resend did not confirm email acceptance; delivery is unconfirmed")


def send_email(
    text: str,
    recipients: list[str],
    subject: str = "Message",
) -> None:
    """
    Send an email using EMAIL_PROVIDER (gmail by default, or resend).

    Args:
        text: The body of the email.
        recipients: List of recipient email addresses.
        subject: Email subject line.

    Raises:
        RuntimeError: If provider settings are missing or sending fails.
    """
    if not recipients:
        raise ValueError("At least one recipient is required")
    provider = (_clean_env_value("EMAIL_PROVIDER") or "gmail").lower()
    if provider == "resend":
        _send_via_resend(text, recipients, subject)
        return
    if provider != "gmail":
        raise ValueError("EMAIL_PROVIDER must be gmail or resend")
    email = _clean_env_value("GMAIL_EMAIL")
    password = _clean_env_value("GMAIL_APP_PASSWORD")

    if not email:
        raise RuntimeError("GMAIL_EMAIL is not set in .env")
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD is not set in .env")

    msg = _build_message(email, recipients, subject, text)

    try:
        _send_via_starttls(email, password, recipients, msg)
    except smtplib.SMTPRecipientsRefused as exc:
        # Some recipients may already have received it. Do not resend to everyone.
        _raise_helpful_smtp_error(exc)
    except Exception as starttls_exc:
        try:
            _send_via_ssl(email, password, recipients, msg)
        except Exception as ssl_exc:
            preferred_exc = ssl_exc if isinstance(ssl_exc, smtplib.SMTPException) else starttls_exc
            _raise_helpful_smtp_error(preferred_exc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send email via Gmail SMTP or Resend HTTPS to a list of recipients"
    )
    parser.add_argument(
        "text",
        help="The email body text",
    )
    parser.add_argument(
        "recipients",
        nargs="+",
        help="One or more recipient email addresses",
    )
    parser.add_argument(
        "-s",
        "--subject",
        default="Message",
        help="Email subject (default: Message)",
    )
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
