"""
Classification model - AI classification of content abuse categories.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from sqlalchemy import String, Enum, Integer, Float, Boolean, JSON, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.content_item import ContentItem
    from app.models.athlete import Athlete
    from app.models.user import User


class ClassificationCategory(str, enum.Enum):
    """Primary classification categories for content abuse."""
    NORMAL_CRITICISM = "normal_criticism"
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    SEXUAL_HARASSMENT = "sexual_harassment"
    THREAT_OF_VIOLENCE = "threat_of_violence"
    DOXXING = "doxxing"
    IMPERSONATION = "impersonation"
    FAKE_QUOTE = "fake_quote"
    FAKE_ENDORSEMENT = "fake_endorsement"
    DEEPFAKE = "deepfake"
    COORDINATED_ATTACK = "coordinated_attack"
    GAMBLING_ABUSE = "gambling_abuse"


class ClassificationStatus(str, enum.Enum):
    """Status of classification review."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


class Classification(Base):
    """
    AI classification of content for abuse detection.

    Each content item receives one or more classifications with
    severity levels and confidence scores.
    """

    __tablename__ = "classifications"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content_item_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE")
    )
    athlete_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE")
    )

    # Classification version for tracking model changes
    classification_version: Mapped[str] = mapped_column(String(50), default="1.0")

    # Categories
    primary_category: Mapped[ClassificationCategory] = mapped_column(
        Enum(ClassificationCategory), nullable=False
    )
    secondary_categories: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=[]
    )

    # Severity and confidence
    severity_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0-1.0

    # Reasoning and evidence
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    key_evidence: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    # Detected entities
    detected_entities: Mapped[dict] = mapped_column(
        JSON,
        default={
            "threats": [],
            "personal_info": [],
            "hate_keywords": [],
            "coordinated_indicators": {}
        }
    )

    # Model information
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'claude-3-5-sonnet'

    # Human review
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    human_review_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    human_reviewer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    human_override_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[ClassificationStatus] = mapped_column(
        Enum(ClassificationStatus), default=ClassificationStatus.PENDING
    )

    # Recommended action
    recommended_action: Mapped[str] = mapped_column(
        String(50), default="monitor"
    )  # monitor, hide, escalate, takedown

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    content_item: Mapped["ContentItem"] = relationship(
        "ContentItem", back_populates="classifications"
    )
    athlete: Mapped["Athlete"] = relationship("Athlete")
    human_reviewer: Mapped[Optional["User"]] = relationship("User")

    # Indexes
    __table_args__ = (
        Index("ix_classification_content", "content_item_id"),
        Index("ix_classification_athlete_severity", "athlete_id", "severity_level"),
        Index("ix_classification_category", "primary_category"),
        Index("ix_classification_created", "created_at"),
        Index("ix_classification_status", "status"),
    )

    @property
    def requires_immediate_review(self) -> bool:
        """Check if classification requires immediate human review."""
        return self.severity_level >= 4

    @property
    def is_high_severity(self) -> bool:
        """Check if classification is high severity (3+)."""
        return self.severity_level >= 3

    def __repr__(self) -> str:
        return f"<Classification(id={self.id}, category={self.primary_category}, severity={self.severity_level})>"
