"""
Content API endpoints for viewing and managing monitored content.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID

from app.database import get_db
from app.models.content_item import ContentItem, ContentType
from app.models.classification import Classification, ClassificationCategory
from app.models.athlete import Athlete
from app.models.user import User
from app.api.auth import get_current_user, require_permission


router = APIRouter(prefix="/content", tags=["content"])


# Pydantic schemas
class ContentItemResponse(BaseModel):
    """Schema for content item response."""
    id: UUID
    athlete_id: UUID
    social_account_id: UUID
    platform: str
    content_type: str
    platform_content_id: str
    author_username: str
    author_display_name: str
    author_profile_url: str
    author_follower_count: int
    content_text: Optional[str]
    content_url: str
    media_urls: List[str]
    engagement_metrics: dict
    discovered_at: datetime
    published_at: datetime

    # Include classification if available
    classification: Optional[dict] = None
    evidence_count: int = 0

    class Config:
        from_attributes = True


class ContentFilterParams(BaseModel):
    """Parameters for filtering content."""
    athlete_id: Optional[UUID] = None
    platform: Optional[str] = None
    content_type: Optional[ContentType] = None
    severity_min: Optional[int] = None
    severity_max: Optional[int] = None
    category: Optional[ClassificationCategory] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search_text: Optional[str] = None


@router.get("", response_model=List[ContentItemResponse])
async def list_content(
    athlete_id: Optional[UUID] = Query(None),
    platform: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    severity_min: Optional[int] = Query(None, ge=1, le=5),
    severity_max: Optional[int] = Query(None, ge=1, le=5),
    category: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    search_text: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    List content items with optional filtering.

    Supports filtering by athlete, platform, content type, severity, category, date range, and text search.
    """
    # Build base query
    query = select(ContentItem).where(
        ContentItem.athlete_id.in_(
            select(Athlete.id).where(Athlete.organization_id == current_user.organization_id)
        )
    )

    # Apply filters
    if athlete_id:
        query = query.where(ContentItem.athlete_id == athlete_id)

    if platform:
        query = query.where(ContentItem.platform == platform)

    if content_type:
        query = query.where(ContentItem.content_type == content_type)

    if start_date:
        query = query.where(ContentItem.discovered_at >= start_date)

    if end_date:
        query = query.where(ContentItem.discovered_at <= end_date)

    if search_text:
        query = query.where(ContentItem.content_text.ilike(f"%{search_text}%"))

    # Filter by severity or category requires join with classifications
    if severity_min or severity_max or category:
        query = query.join(Classification, ContentItem.id == Classification.content_item_id)

        if severity_min:
            query = query.where(Classification.severity_level >= severity_min)

        if severity_max:
            query = query.where(Classification.severity_level <= severity_max)

        if category:
            query = query.where(Classification.primary_category == category)

    # Order by discovery time (newest first)
    query = query.order_by(ContentItem.discovered_at.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    content_items = result.scalars().all()

    # Enrich with classification and evidence count
    response_items = []
    for item in content_items:
        # Get latest classification
        class_query = select(Classification).where(
            Classification.content_item_id == item.id
        ).order_by(Classification.created_at.desc()).limit(1)

        class_result = await db.execute(class_query)
        classification = class_result.scalar_one_or_none()

        # Get evidence count
        from app.models.evidence import Evidence
        evidence_query = select(Evidence).where(Evidence.content_item_id == item.id)
        evidence_result = await db.execute(evidence_query)
        evidence_count = len(evidence_result.scalars().all())

        item_dict = {
            "id": item.id,
            "athlete_id": item.athlete_id,
            "social_account_id": item.social_account_id,
            "platform": item.platform,
            "content_type": item.content_type.value,
            "platform_content_id": item.platform_content_id,
            "author_username": item.author_username,
            "author_display_name": item.author_display_name,
            "author_profile_url": item.author_profile_url,
            "author_follower_count": item.author_follower_count,
            "content_text": item.content_text,
            "content_url": item.content_url,
            "media_urls": item.media_urls,
            "engagement_metrics": item.engagement_metrics,
            "discovered_at": item.discovered_at,
            "published_at": item.published_at,
            "classification": {
                "id": str(classification.id),
                "primary_category": classification.primary_category.value,
                "severity_level": classification.severity_level,
                "confidence_score": classification.confidence_score,
                "status": classification.status.value
            } if classification else None,
            "evidence_count": evidence_count
        }

        response_items.append(ContentItemResponse(**item_dict))

    return response_items


@router.get("/{content_id}", response_model=ContentItemResponse)
async def get_content(
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Get a specific content item by ID.

    Includes classification and evidence information.
    """
    # Get content item
    content_item = await db.get(ContentItem, content_id)

    if not content_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )

    # Check organization access
    athlete = await db.get(Athlete, content_item.athlete_id)
    if athlete.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get classification
    class_query = select(Classification).where(
        Classification.content_item_id == content_item.id
    ).order_by(Classification.created_at.desc()).limit(1)

    class_result = await db.execute(class_query)
    classification = class_result.scalar_one_or_none()

    # Get evidence count
    from app.models.evidence import Evidence
    evidence_query = select(Evidence).where(Evidence.content_item_id == content_item.id)
    evidence_result = await db.execute(evidence_query)
    evidence_count = len(evidence_result.scalars().all())

    item_dict = {
        "id": content_item.id,
        "athlete_id": content_item.athlete_id,
        "social_account_id": content_item.social_account_id,
        "platform": content_item.platform,
        "content_type": content_item.content_type.value,
        "platform_content_id": content_item.platform_content_id,
        "author_username": content_item.author_username,
        "author_display_name": content_item.author_display_name,
        "author_profile_url": content_item.author_profile_url,
        "author_follower_count": content_item.author_follower_count,
        "content_text": content_item.content_text,
        "content_url": content_item.content_url,
        "media_urls": content_item.media_urls,
        "engagement_metrics": content_item.engagement_metrics,
        "discovered_at": content_item.discovered_at,
        "published_at": content_item.published_at,
        "classification": {
            "id": str(classification.id),
            "primary_category": classification.primary_category.value,
            "secondary_categories": classification.secondary_categories,
            "severity_level": classification.severity_level,
            "confidence_score": classification.confidence_score,
            "reasoning": classification.reasoning,
            "key_evidence": classification.key_evidence,
            "detected_entities": classification.detected_entities,
            "model_used": classification.model_used,
            "recommended_action": classification.recommended_action,
            "status": classification.status.value,
            "human_reviewed": classification.human_reviewed
        } if classification else None,
        "evidence_count": evidence_count
    }

    return ContentItemResponse(**item_dict)


@router.post("/{content_id}/hide")
async def hide_content(
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Mark content as hidden from athlete view.

    This sets a flag but doesn't delete the content.
    """
    # TODO: Implement content hiding logic
    # This would update athlete settings or create a hidden_content mapping
    return {"message": "Content hidden successfully", "content_id": str(content_id)}


@router.post("/{content_id}/mark-false-positive")
async def mark_false_positive(
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Mark classification as false positive.

    Updates classification status and can be used for model improvement.
    """
    # Get content's classification
    class_query = select(Classification).where(
        Classification.content_item_id == content_id
    ).order_by(Classification.created_at.desc()).limit(1)

    class_result = await db.execute(class_query)
    classification = class_result.scalar_one_or_none()

    if not classification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classification not found"
        )

    # Update status
    from app.models.classification import ClassificationStatus
    classification.status = ClassificationStatus.FALSE_POSITIVE
    classification.human_reviewed = True
    classification.human_review_at = datetime.utcnow()
    classification.human_reviewer_id = current_user.id

    await db.commit()

    return {
        "message": "Marked as false positive",
        "classification_id": str(classification.id)
    }


@router.get("/{content_id}/timeline")
async def get_content_timeline(
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Get timeline of events for a content item.

    Returns discovery, classification, evidence capture, and review events.
    """
    content_item = await db.get(ContentItem, content_id)

    if not content_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )

    timeline = []

    # Discovery event
    timeline.append({
        "timestamp": content_item.discovered_at,
        "event_type": "discovered",
        "description": f"Content discovered on {content_item.platform}",
        "actor": "system"
    })

    # Classification events
    class_query = select(Classification).where(
        Classification.content_item_id == content_id
    ).order_by(Classification.created_at)

    class_result = await db.execute(class_query)
    classifications = class_result.scalars().all()

    for classification in classifications:
        timeline.append({
            "timestamp": classification.created_at,
            "event_type": "classified",
            "description": f"Classified as {classification.primary_category.value} (severity {classification.severity_level})",
            "actor": "system",
            "details": {
                "category": classification.primary_category.value,
                "severity": classification.severity_level,
                "confidence": classification.confidence_score
            }
        })

        if classification.human_reviewed:
            timeline.append({
                "timestamp": classification.human_review_at,
                "event_type": "reviewed",
                "description": f"Human review: {classification.status.value}",
                "actor": str(classification.human_reviewer_id) if classification.human_reviewer_id else "unknown"
            })

    # Evidence events
    from app.models.evidence import Evidence
    evidence_query = select(Evidence).where(
        Evidence.content_item_id == content_id
    ).order_by(Evidence.created_at)

    evidence_result = await db.execute(evidence_query)
    evidence_items = evidence_result.scalars().all()

    for evidence in evidence_items:
        timeline.append({
            "timestamp": evidence.created_at,
            "event_type": "evidence_captured",
            "description": f"Evidence captured: {evidence.evidence_type.value}",
            "actor": "system",
            "details": {
                "type": evidence.evidence_type.value,
                "size": evidence.file_size
            }
        })

    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"])

    return {"content_id": str(content_id), "timeline": timeline}
