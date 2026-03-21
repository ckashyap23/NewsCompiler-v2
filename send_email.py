"""
Send email via Gmail SMTP to a list of recipients.

Usage:
    python send_email.py "Your message text" recipient1@example.com recipient2@example.com
    python send_email.py -s "Subject" "Your message text" recipient@example.com

Sender email is read from GMAIL_EMAIL in .env.
Password (Gmail App Password) is read from GMAIL_APP_PASSWORD in .env.
"""
import argparse
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
import os

load_dotenv()

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


def send_email(
    text: str,
    recipients: list[str],
    subject: str = "Message",
) -> None:
    """
    Send an email via Gmail to the given recipients.

    Args:
        text: The body of the email.
        recipients: List of recipient email addresses.
        subject: Email subject line.

    Raises:
        RuntimeError: If GMAIL_EMAIL or GMAIL_APP_PASSWORD are not set.
        smtplib.SMTPException: On SMTP errors.
    """
    email = (os.getenv("GMAIL_EMAIL") or "").strip()
    password = (os.getenv("GMAIL_APP_PASSWORD") or "").replace(" ", "").strip()

    if not email:
        raise RuntimeError("GMAIL_EMAIL is not set in .env")
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD is not set in .env")
    if not recipients:
        raise ValueError("At least one recipient is required")

    msg = MIMEMultipart()
    msg["From"] = email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(text, "plain"))

    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(email, password)
        smtp.sendmail(email, recipients, msg.as_string())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send email via Gmail to a list of recipients"
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
