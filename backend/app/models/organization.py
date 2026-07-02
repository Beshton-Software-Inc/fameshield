"""
Organization model - represents sports federations, schools, agencies, etc.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4
from sqlalchemy import String, Enum, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.athlete import Athlete


class OrganizationType(str, enum.Enum):
    """Types of organizations."""
    FEDERATION = "federation"
    SCHOOL = "school"
    AGENCY = "agency"
    CLUB = "club"
    INDIVIDUAL = "individual"


class OrganizationTier(str, enum.Enum):
    """Subscription tiers."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Organization(Base):
    """Organization model."""

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    tier: Mapped[OrganizationTier] = mapped_column(
        Enum(OrganizationTier, values_callable=lambda x: [e.value for e in x]),
        default=OrganizationTier.STARTER,
    )

    # JSON settings for flexibility
    settings: Mapped[dict] = mapped_column(
        JSON,
        default={
            "monitoring_frequency": 15,  # minutes
            "severity_thresholds": {},
            "escalation_rules": {},
            "allowed_platforms": ["twitter", "instagram", "tiktok", "youtube"]
        }
    )

    billing_info: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )
    athletes: Mapped[list["Athlete"]] = relationship(
        "Athlete", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, type={self.type})>"
