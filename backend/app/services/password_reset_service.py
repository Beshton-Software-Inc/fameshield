"""Password reset primitives shared between athlete and staff auth."""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.password_reset import PasswordResetToken
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

Audience = Literal["athlete", "staff"]
TOKEN_TTL = timedelta(hours=1)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _reset_url(raw_token: str, audience: Audience) -> str:
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/reset-password?token={raw_token}&type={audience}"


async def create_reset_token(
    db: AsyncSession, subject_id: UUID, audience: Audience
) -> tuple[str, PasswordResetToken]:
    """Mint a token, persist its hash, return (raw_token, row)."""
    raw = secrets.token_urlsafe(32)
    row = PasswordResetToken(
        audience=audience,
        subject_id=subject_id,
        token_hash=_hash(raw),
        expires_at=datetime.utcnow() + TOKEN_TTL,
    )
    db.add(row)
    await db.flush()
    return raw, row


async def consume_token(
    db: AsyncSession, raw_token: str, audience: Audience
) -> Optional[UUID]:
    """Return the subject_id if the token is valid+unused, else None. Marks it used."""
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == _hash(raw_token),
            PasswordResetToken.audience == audience,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return None
    if token.used_at is not None:
        return None
    if token.expires_at.replace(tzinfo=None) < datetime.utcnow():
        return None
    token.used_at = datetime.utcnow()
    return token.subject_id


def send_reset_email(to: str, name: Optional[str], raw_token: str, audience: Audience) -> None:
    url = _reset_url(raw_token, audience)
    greeting = f"Hi {name}," if name else "Hi,"
    subject = "Reset your FameShield password"
    body = (
        f"{greeting}\n\n"
        "We received a request to reset the password on your FameShield account. "
        "Click the link below to choose a new one. The link expires in 1 hour.\n\n"
        f"{url}\n\n"
        "If you didn't request this, you can ignore this email — your password stays the same.\n\n"
        "— FameShield"
    )
    html_body = (
        f"<p>{greeting}</p>"
        "<p>We received a request to reset the password on your FameShield account. "
        "Click the link below to choose a new one. The link expires in 1 hour.</p>"
        f'<p><a href="{url}">Reset your password</a></p>'
        f'<p style="color:#888;font-size:12px">Or paste this URL: {url}</p>'
        "<p>If you didn't request this, you can ignore this email — your password stays the same.</p>"
        "<p>— FameShield</p>"
    )
    send_email(to, subject, body, html_body=html_body)
