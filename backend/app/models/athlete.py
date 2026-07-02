"""
Athlete model - represents the athletes being protected.
"""
from datetime import datetime, date
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from sqlalchemy import String, Enum, JSON, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.social_account import SocialAccount
    from app.models.content_item import ContentItem
    from app.models.subscription import AthleteSubscription, PaymentMethod


class RiskLevel(str, enum.Enum):
    """Athlete risk level based on abuse patterns."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentFilteringLevel(str, enum.Enum):
    """Level of content filtering for athlete dashboard."""
    NONE = "none"
    MODERATE = "moderate"
    STRICT = "strict"


class Athlete(Base):
    """Athlete model."""

    __tablename__ = "athletes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)

    sport: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)

    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, values_callable=lambda x: [e.value for e in x]),
        default=RiskLevel.LOW,
    )

    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    settings: Mapped[dict] = mapped_column(
        JSON,
        default={
            "content_filtering_level": "moderate",
            "auto_hide_threshold": 3,  # Severity level
            "notification_preferences": {
                "email_enabled": True,
                "severity_threshold": 4
            },
            "dashboard_access": True
        }
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_monitored_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="athletes"
    )
    social_accounts: Mapped[list["SocialAccount"]] = relationship(
        "SocialAccount", back_populates="athlete", cascade="all, delete-orphan"
    )
    content_items: Mapped[list["ContentItem"]] = relationship(
        "ContentItem", back_populates="athlete", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["AthleteSubscription"]] = relationship(
        "AthleteSubscription", back_populates="athlete", cascade="all, delete-orphan"
    )
    payment_methods: Mapped[list["PaymentMethod"]] = relationship(
        "PaymentMethod", back_populates="athlete", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """Get athlete's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        """Calculate athlete's current age."""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def is_youth(self) -> bool:
        """Check if athlete is under 18."""
        return self.age < 18

    def __repr__(self) -> str:
        return f"<Athlete(id={self.id}, name={self.full_name}, sport={self.sport})>"
