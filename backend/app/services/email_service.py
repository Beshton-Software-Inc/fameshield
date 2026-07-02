"""Email sender. Falls back to logging when SMTP creds are missing so the
password-reset flow is testable without hooking up a real mailbox.
"""
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.smtp_user and settings.smtp_password)


def send_email(to: str, subject: str, body: str, html_body: Optional[str] = None) -> None:
    """Send an email via configured SMTP.

    When SMTP credentials are absent, log the message body to the backend log
    instead of raising — the caller doesn't need to know which branch ran.
    """
    if not is_configured():
        logger.warning(
            "[email:log-only] SMTP not configured. Would send:\n"
            "  to:      %s\n"
            "  from:    %s\n"
            "  subject: %s\n"
            "  body:\n%s",
            to,
            settings.from_email,
            subject,
            body,
        )
        return

    msg = EmailMessage()
    msg["From"] = settings.from_email
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)  # type: ignore[arg-type]
                smtp.send_message(msg)
        else:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                smtp.login(settings.smtp_user, settings.smtp_password)  # type: ignore[arg-type]
                smtp.send_message(msg)
        logger.info("Sent email to %s (subject=%r)", to, subject)
    except Exception:
        # Don't leak SMTP errors to the API surface — a reset request must
        # look identical to the caller whether we sent or not.
        logger.exception("SMTP send failed for %s", to)
