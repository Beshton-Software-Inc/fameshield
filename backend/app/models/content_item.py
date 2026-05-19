"""
ContentItem model - represents social media content being monitored.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
from uuid import uuid4
from sqlalchemy import String, Enum, Integer, JSON, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.athlete import Athlete
    from app.models.social_account import SocialAccount
    from app.models.classification import Classification
    from app.models.evidence import Evidence


class ContentType(str, enum.Enum):
    """Types of social media content."""
    POST = "post"
    COMMENT = "comment"
    MENTION = "mention"
    DM = "dm"
    STORY = "story"
    VIDEO = "video"
    REPLY = "reply"


class ContentItem(Base):
    """
    Social media content item being monitored.

    Represents any piece of content (post, comment, mention, etc.)
    from social media platforms that mentions or involves an athlete.
    """

    __tablename__ = "content_items"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    athlete_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE")
    )
    social_account_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("social_accounts.id", ondelete="CASCADE")
    )

    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    content_type: Mapped[ContentType] = mapped_column(Enum(ContentType), nullable=False)

    # Platform-specific identifiers
    platform_content_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Author information
    author_platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_username: Mapped[str] = mapped_column(String(255), nullable=False)
    author_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_profile_url: Mapped[str] = mapped_column(String(500), nullable=False)
    author_follower_count: Mapped[int] = mapped_column(Integer, default=0)

    # Content
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_url: Mapped[str] = mapped_column(String(500), nullable=False)
    media_urls: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    # Parent content (for replies/comments)
    parent_content_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True
    )

    # Engagement metrics
    engagement_metrics: Mapped[dict] = mapped_column(
        JSON,
        default={
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "views": 0
        }
    )

    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    athlete: Mapped["Athlete"] = relationship("Athlete", back_populates="content_items")
    social_account: Mapped["SocialAccount"] = relationship("SocialAccount")
    classifications: Mapped[List["Classification"]] = relationship(
        "Classification", back_populates="content_item", cascade="all, delete-orphan"
    )
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="content_item", cascade="all, delete-orphan"
    )

    # Self-referential relationship for replies
    parent_content: Mapped[Optional["ContentItem"]] = relationship(
        "ContentItem", remote_side=[id], back_populates="replies"
    )
    replies: Mapped[List["ContentItem"]] = relationship(
        "ContentItem", back_populates="parent_content"
    )

    # Indexes defined in table args
    __table_args__ = (
        Index("ix_content_athlete_discovered", "athlete_id", "discovered_at"),
        Index("ix_content_platform_id", "platform", "platform_content_id", unique=True),
        Index("ix_content_author", "author_platform_id"),
        Index("ix_content_published", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<ContentItem(id={self.id}, platform={self.platform}, type={self.content_type})>"


# Update athlete model to include relationship (add to athlete.py later)
# content_items: Mapped[List["ContentItem"]] = relationship("ContentItem", back_populates="athlete")
