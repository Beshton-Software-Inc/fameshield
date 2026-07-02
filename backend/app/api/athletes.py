"""
Athlete management API endpoints.
"""
from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models.athlete import Athlete, RiskLevel, ContentFilteringLevel
from app.models.user import User
from app.api.auth import get_current_user, require_permission


router = APIRouter(prefix="/athletes", tags=["athletes"])


# Pydantic schemas
class AthleteCreate(BaseModel):
    """Schema for creating an athlete."""
    first_name: str
    last_name: str
    email: EmailStr
    date_of_birth: date
    sport: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    monitoring_enabled: bool = True


class AthleteUpdate(BaseModel):
    """Schema for updating an athlete."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    sport: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    monitoring_enabled: Optional[bool] = None
    settings: Optional[dict] = None


class AthleteResponse(BaseModel):
    """Schema for athlete response."""
    id: UUID
    organization_id: Optional[UUID] = None
    first_name: str
    last_name: str
    full_name: str
    email: str
    date_of_birth: date
    age: int
    is_youth: bool
    sport: str
    bio: Optional[str]
    profile_image_url: Optional[str]
    risk_level: RiskLevel
    monitoring_enabled: bool
    settings: dict
    created_at: datetime
    updated_at: datetime
    last_monitored_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.post("", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
async def create_athlete(
    athlete_data: AthleteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_athletes"))
):
    """
    Create a new athlete profile.

    Requires 'view_athletes' permission.
    """
    # Check if athlete email already exists in this organization
    result = await db.execute(
        select(Athlete).where(
            Athlete.organization_id == current_user.organization_id,
            Athlete.email == athlete_data.email
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Athlete with this email already exists in your organization"
        )

    # Create athlete
    athlete = Athlete(
        organization_id=current_user.organization_id,
        **athlete_data.model_dump()
    )
    db.add(athlete)
    await db.commit()
    await db.refresh(athlete)

    return athlete


@router.get("", response_model=List[AthleteResponse])
async def list_athletes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    sport: Optional[str] = None,
    risk_level: Optional[RiskLevel] = None,
    monitoring_enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_athletes"))
):
    """
    List athletes in the current user's organization.

    Supports filtering by sport, risk_level, and monitoring status.
    """
    query = select(Athlete).where(
        Athlete.organization_id == current_user.organization_id
    )

    # Apply filters
    if sport:
        query = query.where(Athlete.sport == sport)
    if risk_level:
        query = query.where(Athlete.risk_level == risk_level)
    if monitoring_enabled is not None:
        query = query.where(Athlete.monitoring_enabled == monitoring_enabled)

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    athletes = result.scalars().all()

    return athletes


@router.get("/{athlete_id}", response_model=AthleteResponse)
async def get_athlete(
    athlete_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_athletes"))
):
    """
    Get a specific athlete by ID.
    """
    result = await db.execute(
        select(Athlete).where(
            Athlete.id == athlete_id,
            Athlete.organization_id == current_user.organization_id
        )
    )
    athlete = result.scalar_one_or_none()

    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )

    return athlete


@router.patch("/{athlete_id}", response_model=AthleteResponse)
async def update_athlete(
    athlete_id: UUID,
    athlete_data: AthleteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_athletes"))
):
    """
    Update an athlete's information.
    """
    result = await db.execute(
        select(Athlete).where(
            Athlete.id == athlete_id,
            Athlete.organization_id == current_user.organization_id
        )
    )
    athlete = result.scalar_one_or_none()

    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )

    # Update fields
    update_data = athlete_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(athlete, field, value)

    athlete.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(athlete)

    return athlete


@router.delete("/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_athlete(
    athlete_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_athletes"))
):
    """
    Delete an athlete profile.

    This will also delete all associated social accounts and content.
    """
    result = await db.execute(
        select(Athlete).where(
            Athlete.id == athlete_id,
            Athlete.organization_id == current_user.organization_id
        )
    )
    athlete = result.scalar_one_or_none()

    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )

    await db.delete(athlete)
    await db.commit()

    return None


@router.get("/{athlete_id}/dashboard-stats")
async def get_athlete_dashboard_stats(
    athlete_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_athletes"))
):
    """
    Get dashboard statistics for an athlete.

    Returns summary stats for content monitoring.
    """
    result = await db.execute(
        select(Athlete).where(
            Athlete.id == athlete_id,
            Athlete.organization_id == current_user.organization_id
        )
    )
    athlete = result.scalar_one_or_none()

    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )

    # TODO: Implement actual stats calculation once content models are added
    stats = {
        "athlete_id": str(athlete.id),
        "total_content_monitored": 0,
        "flagged_content": 0,
        "high_severity_count": 0,
        "last_monitored": athlete.last_monitored_at,
        "risk_level": athlete.risk_level,
        "social_accounts_connected": 0,  # Will be calculated from relationships
    }

    return stats


@router.patch("/{athlete_id}/settings")
async def update_athlete_settings(
    athlete_id: UUID,
    settings: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("view_athletes"))
):
    """
    Update athlete-specific settings.
    """
    result = await db.execute(
        select(Athlete).where(
            Athlete.id == athlete_id,
            Athlete.organization_id == current_user.organization_id
        )
    )
    athlete = result.scalar_one_or_none()

    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )

    # Merge settings
    current_settings = athlete.settings or {}
    current_settings.update(settings)
    athlete.settings = current_settings
    athlete.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(athlete)

    return {"message": "Settings updated successfully", "settings": athlete.settings}
