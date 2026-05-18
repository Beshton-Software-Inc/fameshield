"""
User model - represents admin, coaches, agents, staff members.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from sqlalchemy import String, Enum, JSON, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class UserRole(str, enum.Enum):
    """User roles with different permission levels."""
    ADMIN = "admin"
    COACH = "coach"
    AGENT = "agent"
    MENTAL_HEALTH_STAFF = "mental_health_staff"
    LEGAL = "legal"
    VIEWER = "viewer"


class User(Base):
    """User model for organization staff members."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Which athletes this user can access (empty = all)
    athlete_access: Mapped[list[str]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=[]
    )

    notification_preferences: Mapped[dict] = mapped_column(
        JSON,
        default={
            "email_enabled": True,
            "sms_enabled": False,
            "severity_threshold": 3
        }
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="users"
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        if self.role == UserRole.ADMIN:
            return True
        return permission in self.permissions

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
