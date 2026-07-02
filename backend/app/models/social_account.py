"""
SocialAccount model - represents athlete's connected social media accounts.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from sqlalchemy import String, Enum, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.athlete import Athlete


class Platform(str, enum.Enum):
    """Supported social media platforms."""
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"


class MonitoringStatus(str, enum.Enum):
    """Status of monitoring for this account."""
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class SocialAccount(Base):
    """Social media account linked to an athlete."""

    __tablename__ = "social_accounts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    athlete_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE")
    )

    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_url: Mapped[str] = mapped_column(String(500), nullable=False)

    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Encrypted in application layer before storing
    access_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    monitoring_status: Mapped[MonitoringStatus] = mapped_column(
        Enum(MonitoringStatus, values_callable=lambda x: [e.value for e in x]),
        default=MonitoringStatus.ACTIVE,
    )

    last_monitored_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    athlete: Mapped["Athlete"] = relationship(
        "Athlete", back_populates="social_accounts"
    )

    @property
    def is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (within 1 hour of expiry)."""
        if not self.token_expires_at:
            return False
        time_until_expiry = (self.token_expires_at - datetime.utcnow()).total_seconds()
        return time_until_expiry < 3600  # Less than 1 hour

    def __repr__(self) -> str:
        return f"<SocialAccount(id={self.id}, platform={self.platform}, username={self.username})>"
