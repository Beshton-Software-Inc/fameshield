"""
Classification API endpoints for viewing and managing classifications.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.models.classification import Classification, ClassificationCategory, ClassificationStatus
from app.models.content_item import ContentItem
from app.models.athlete import Athlete
from app.models.user import User
from app.api.auth import get_current_user, require_permission


router = APIRouter(prefix="/classifications", tags=["classifications"])


# Pydantic schemas
class ClassificationResponse(BaseModel):
    """Schema for classification response."""
    id: UUID
    content_item_id: UUID
    athlete_id: UUID
    primary_category: str
    secondary_categories: List[str]
    severity_level: int
    confidence_score: float
    reasoning: str
    key_evidence: List[str]
    detected_entities: dict
    model_used: str
    recommended_action: str
    status: str
    human_reviewed: bool
    human_review_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ClassificationReviewRequest(BaseModel):
    """Schema for human review of classification."""
    status: ClassificationStatus
    override_category: Optional[ClassificationCategory] = None
    notes: Optional[str] = None


@router.get("", response_model=List[ClassificationResponse])
async def list_classifications(
    athlete_id: Optional[UUID] = Query(None),
    category: Optional[ClassificationCategory] = Query(None),
    severity_min: Optional[int] = Query(None, ge=1, le=5),
    severity_max: Optional[int] = Query(None, ge=1, le=5),
    status: Optional[ClassificationStatus] = Query(None),
    requires_review: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    List classifications with optional filtering.

    Supports filtering by athlete, category, severity, status, and review status.
    """
    # Build base query
    query = select(Classification).join(
        Athlete, Classification.athlete_id == Athlete.id
    ).where(Athlete.organization_id == current_user.organization_id)

    # Apply filters
    if athlete_id:
        query = query.where(Classification.athlete_id == athlete_id)

    if category:
        query = query.where(Classification.primary_category == category)

    if severity_min:
        query = query.where(Classification.severity_level >= severity_min)

    if severity_max:
        query = query.where(Classification.severity_level <= severity_max)

    if status:
        query = query.where(Classification.status == status)

    if requires_review is not None:
        if requires_review:
            query = query.where(Classification.severity_level >= 4, Classification.human_reviewed == False)
        else:
            query = query.where(Classification.human_reviewed == True)

    # Order by severity (highest first), then by created date (newest first)
    query = query.order_by(
        Classification.severity_level.desc(),
        Classification.created_at.desc()
    )

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    classifications = result.scalars().all()

    return [
        ClassificationResponse(
            id=c.id,
            content_item_id=c.content_item_id,
            athlete_id=c.athlete_id,
            primary_category=c.primary_category.value,
            secondary_categories=c.secondary_categories,
            severity_level=c.severity_level,
            confidence_score=c.confidence_score,
            reasoning=c.reasoning,
            key_evidence=c.key_evidence,
            detected_entities=c.detected_entities,
            model_used=c.model_used,
            recommended_action=c.recommended_action,
            status=c.status.value,
            human_reviewed=c.human_reviewed,
            human_review_at=c.human_review_at,
            created_at=c.created_at
        )
        for c in classifications
    ]


@router.get("/{classification_id}", response_model=ClassificationResponse)
async def get_classification(
    classification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Get a specific classification by ID.
    """
    classification = await db.get(Classification, classification_id)

    if not classification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classification not found"
        )

    # Check organization access
    athlete = await db.get(Athlete, classification.athlete_id)
    if athlete.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return ClassificationResponse(
        id=classification.id,
        content_item_id=classification.content_item_id,
        athlete_id=classification.athlete_id,
        primary_category=classification.primary_category.value,
        secondary_categories=classification.secondary_categories,
        severity_level=classification.severity_level,
        confidence_score=classification.confidence_score,
        reasoning=classification.reasoning,
        key_evidence=classification.key_evidence,
        detected_entities=classification.detected_entities,
        model_used=classification.model_used,
        recommended_action=classification.recommended_action,
        status=classification.status.value,
        human_reviewed=classification.human_reviewed,
        human_review_at=classification.human_review_at,
        created_at=classification.created_at
    )


@router.patch("/{classification_id}/review", response_model=ClassificationResponse)
async def review_classification(
    classification_id: UUID,
    review: ClassificationReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Submit human review for a classification.

    Allows staff to confirm, mark as false positive, or override the AI classification.
    """
    classification = await db.get(Classification, classification_id)

    if not classification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classification not found"
        )

    # Check organization access
    athlete = await db.get(Athlete, classification.athlete_id)
    if athlete.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update classification
    classification.status = review.status
    classification.human_reviewed = True
    classification.human_review_at = datetime.utcnow()
    classification.human_reviewer_id = current_user.id

    if review.override_category:
        classification.human_override_category = review.override_category.value

    await db.commit()
    await db.refresh(classification)

    return ClassificationResponse(
        id=classification.id,
        content_item_id=classification.content_item_id,
        athlete_id=classification.athlete_id,
        primary_category=classification.primary_category.value,
        secondary_categories=classification.secondary_categories,
        severity_level=classification.severity_level,
        confidence_score=classification.confidence_score,
        reasoning=classification.reasoning,
        key_evidence=classification.key_evidence,
        detected_entities=classification.detected_entities,
        model_used=classification.model_used,
        recommended_action=classification.recommended_action,
        status=classification.status.value,
        human_reviewed=classification.human_reviewed,
        human_review_at=classification.human_review_at,
        created_at=classification.created_at
    )


@router.post("/{classification_id}/escalate")
async def escalate_classification(
    classification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Manually escalate a classification for immediate attention.

    Triggers the escalation workflow.
    """
    classification = await db.get(Classification, classification_id)

    if not classification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classification not found"
        )

    # Check organization access
    athlete = await db.get(Athlete, classification.athlete_id)
    if athlete.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Trigger escalation
    from app.workers.classify_worker import create_escalation
    task = create_escalation.delay(str(classification_id))

    return {
        "message": "Escalation triggered",
        "classification_id": str(classification_id),
        "task_id": task.id
    }


@router.post("/{classification_id}/reclassify")
async def reclassify(
    classification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Trigger re-classification of content.

    Uses the latest model to re-analyze the content.
    """
    classification = await db.get(Classification, classification_id)

    if not classification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classification not found"
        )

    # Check organization access
    athlete = await db.get(Athlete, classification.athlete_id)
    if athlete.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Trigger reclassification
    from app.workers.classify_worker import reclassify_content
    task = reclassify_content.delay(str(classification_id))

    return {
        "message": "Re-classification triggered",
        "classification_id": str(classification_id),
        "task_id": task.id
    }


@router.get("/statistics/summary")
async def get_classification_statistics(
    athlete_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_content"))
):
    """
    Get classification statistics and summary.

    Returns distribution by category, severity, and trends over time.
    """
    # Build base query
    query = select(Classification).join(
        Athlete, Classification.athlete_id == Athlete.id
    ).where(Athlete.organization_id == current_user.organization_id)

    # Apply filters
    if athlete_id:
        query = query.where(Classification.athlete_id == athlete_id)

    if start_date:
        query = query.where(Classification.created_at >= start_date)

    if end_date:
        query = query.where(Classification.created_at <= end_date)

    # Get all classifications
    result = await db.execute(query)
    classifications = result.scalars().all()

    # Calculate statistics
    total = len(classifications)

    if total == 0:
        return {
            "total": 0,
            "by_category": {},
            "by_severity": {},
            "by_status": {},
            "requires_review": 0,
            "average_confidence": 0
        }

    # Count by category
    by_category = {}
    for c in classifications:
        category = c.primary_category.value
        by_category[category] = by_category.get(category, 0) + 1

    # Count by severity
    by_severity = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for c in classifications:
        by_severity[c.severity_level] += 1

    # Count by status
    by_status = {}
    for c in classifications:
        status = c.status.value
        by_status[status] = by_status.get(status, 0) + 1

    # Count requiring review
    requires_review = sum(1 for c in classifications if c.requires_immediate_review and not c.human_reviewed)

    # Average confidence
    avg_confidence = sum(c.confidence_score for c in classifications) / total

    return {
        "total": total,
        "by_category": by_category,
        "by_severity": by_severity,
        "by_status": by_status,
        "requires_review": requires_review,
        "average_confidence": round(avg_confidence, 3)
    }
