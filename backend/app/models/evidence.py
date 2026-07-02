"""
Evidence model - digital evidence for content and classifications.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4
from sqlalchemy import String, Enum, BigInteger, JSON, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.content_item import ContentItem
    from app.models.classification import Classification
    from app.models.athlete import Athlete


class EvidenceType(str, enum.Enum):
    """Types of evidence."""
    SCREENSHOT = "screenshot"
    VIDEO = "video"
    RAW_HTML = "raw_html"
    METADATA = "metadata"
    API_RESPONSE = "api_response"


class Evidence(Base):
    """
    Digital evidence for content items and classifications.

    Stores screenshots, raw HTML, metadata, and other evidence
    with chain of custody tracking for legal proceedings.
    """

    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content_item_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE")
    )
    classification_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classifications.id", ondelete="CASCADE"), nullable=True
    )
    athlete_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE")
    )

    # Evidence details
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(EvidenceType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # Storage
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # S3 key
    storage_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # Pre-signed URL

    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Integrity
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256

    # Metadata about capture ("metadata" is reserved by SQLAlchemy Declarative)
    capture_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default={
            "capture_timestamp": None,
            "capture_method": "automated",
            "browser_info": {},
            "viewport_size": {},
            "device_info": {}
        }
    )

    # Chain of custody
    chain_of_custody: Mapped[list] = mapped_column(
        JSON,
        default=[]
    )
    # Format: [{"actor_id": "uuid", "actor_type": "system|user|api", "action": "created|viewed|exported", "timestamp": "iso8601", "ip_address": "x.x.x.x"}]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    content_item: Mapped["ContentItem"] = relationship(
        "ContentItem", back_populates="evidence"
    )
    classification: Mapped[Optional["Classification"]] = relationship("Classification")
    athlete: Mapped["Athlete"] = relationship("Athlete")

    # Indexes
    __table_args__ = (
        Index("ix_evidence_content", "content_item_id"),
        Index("ix_evidence_athlete", "athlete_id"),
        Index("ix_evidence_type", "evidence_type"),
        Index("ix_evidence_created", "created_at"),
    )

    def add_custody_entry(
        self,
        actor_id: str,
        actor_type: str,
        action: str,
        ip_address: Optional[str] = None
    ) -> None:
        """Add an entry to the chain of custody."""
        entry = {
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if ip_address:
            entry["ip_address"] = ip_address

        if not self.chain_of_custody:
            self.chain_of_custody = []

        self.chain_of_custody.append(entry)

    def __repr__(self) -> str:
        return f"<Evidence(id={self.id}, type={self.evidence_type}, content={self.content_item_id})>"
