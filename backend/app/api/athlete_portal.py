"""Athlete self-service portal: profile, social accounts, appearances, violations."""
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.athlete_auth import get_current_athlete
from app.database import get_db
from app.models.athlete import Athlete, RiskLevel
from app.models.classification import Classification
from app.models.content_item import ContentItem
from app.models.social_account import MonitoringStatus, Platform, SocialAccount

router = APIRouter(prefix="/me", tags=["athlete-portal"])


class MeResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    full_name: str
    date_of_birth: date
    age: int
    sport: str
    bio: Optional[str] = None
    phone: Optional[str] = None
    profile_image_url: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    risk_level: RiskLevel
    monitoring_enabled: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    sport: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    monitoring_enabled: Optional[bool] = None


class SocialAccountCreate(BaseModel):
    platform: Platform
    username: str
    display_name: Optional[str] = None
    profile_url: Optional[str] = None


class SocialAccountResponse(BaseModel):
    id: UUID
    platform: Platform
    username: str
    display_name: str
    profile_url: str
    follower_count: int
    verified: bool
    monitoring_status: MonitoringStatus
    last_monitored_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlatformAppearance(BaseModel):
    platform: str
    content_total: int
    flagged_total: int
    high_severity_total: int
    last_seen_at: Optional[datetime] = None


class ViolationItem(BaseModel):
    id: UUID
    content_item_id: UUID
    platform: str
    primary_category: str
    severity_level: int
    status: str
    reasoning: str
    content_excerpt: Optional[str] = None
    content_url: Optional[str] = None
    author_username: Optional[str] = None
    created_at: datetime


@router.get("", response_model=MeResponse)
async def get_me(athlete: Athlete = Depends(get_current_athlete)):
    return athlete


@router.patch("/profile", response_model=MeResponse)
async def update_profile(
    payload: ProfileUpdate,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    data = payload.dict(exclude_unset=True)
    if "email" in data and data["email"] != athlete.email:
        clash = await db.execute(select(Athlete).where(Athlete.email == data["email"]))
        if clash.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
            )
    for key, value in data.items():
        setattr(athlete, key, value)
    await db.commit()
    await db.refresh(athlete)
    return athlete


@router.get("/social-accounts", response_model=list[SocialAccountResponse])
async def list_social_accounts(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SocialAccount).where(SocialAccount.athlete_id == athlete.id)
    )
    return list(result.scalars().all())


@router.post(
    "/social-accounts",
    response_model=SocialAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_social_account(
    payload: SocialAccountCreate,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    display_name = payload.display_name or payload.username
    profile_url = payload.profile_url or _default_profile_url(payload.platform, payload.username)
    account = SocialAccount(
        athlete_id=athlete.id,
        platform=payload.platform,
        platform_user_id=payload.username,  # placeholder until platform lookup wired
        username=payload.username,
        display_name=display_name,
        profile_url=profile_url,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/social-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_social_account(
    account_id: UUID,
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id, SocialAccount.athlete_id == athlete.id
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found"
        )
    await db.delete(account)
    await db.commit()


@router.get("/appearances", response_model=list[PlatformAppearance])
async def appearances_by_platform(
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    """Content volume and violation counts per platform for this athlete."""
    content_stmt = (
        select(
            ContentItem.platform.label("platform"),
            func.count(ContentItem.id).label("content_total"),
            func.max(ContentItem.discovered_at).label("last_seen_at"),
        )
        .where(ContentItem.athlete_id == athlete.id)
        .group_by(ContentItem.platform)
    )
    class_stmt = (
        select(
            ContentItem.platform.label("platform"),
            func.count(Classification.id).label("flagged_total"),
            func.sum(
                func.cast(Classification.severity_level >= 3, __sql_int_type())
            ).label("high_severity_total"),
        )
        .join(ContentItem, ContentItem.id == Classification.content_item_id)
        .where(Classification.athlete_id == athlete.id)
        .group_by(ContentItem.platform)
    )

    content_rows = (await db.execute(content_stmt)).all()
    class_rows = (await db.execute(class_stmt)).all()
    class_by_platform = {r.platform: r for r in class_rows}

    return [
        PlatformAppearance(
            platform=row.platform,
            content_total=row.content_total,
            flagged_total=(class_by_platform.get(row.platform).flagged_total if row.platform in class_by_platform else 0),
            high_severity_total=int(
                class_by_platform.get(row.platform).high_severity_total or 0
            ) if row.platform in class_by_platform else 0,
            last_seen_at=row.last_seen_at,
        )
        for row in content_rows
    ]


@router.get("/violations", response_model=list[ViolationItem])
async def list_violations(
    severity_min: Optional[int] = Query(None, ge=1, le=5),
    category: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    athlete: Athlete = Depends(get_current_athlete),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Classification, ContentItem)
        .join(ContentItem, ContentItem.id == Classification.content_item_id)
        .where(Classification.athlete_id == athlete.id)
        .order_by(Classification.created_at.desc())
        .limit(limit)
    )
    if severity_min is not None:
        stmt = stmt.where(Classification.severity_level >= severity_min)
    if category:
        stmt = stmt.where(Classification.primary_category == category)

    rows = (await db.execute(stmt)).all()
    return [
        ViolationItem(
            id=c.id,
            content_item_id=c.content_item_id,
            platform=item.platform,
            primary_category=c.primary_category,
            severity_level=c.severity_level,
            status=(c.status.value if hasattr(c.status, "value") else str(c.status)),
            reasoning=c.reasoning,
            content_excerpt=(item.content_text or "")[:300] if item.content_text else None,
            content_url=item.content_url,
            author_username=item.author_username,
            created_at=c.created_at,
        )
        for c, item in rows
    ]


def _default_profile_url(platform: Platform, username: str) -> str:
    handle = username.lstrip("@")
    return {
        Platform.TWITTER: f"https://x.com/{handle}",
        Platform.INSTAGRAM: f"https://instagram.com/{handle}",
        Platform.TIKTOK: f"https://tiktok.com/@{handle}",
        Platform.YOUTUBE: f"https://youtube.com/@{handle}",
        Platform.FACEBOOK: f"https://facebook.com/{handle}",
    }.get(platform, "")


def __sql_int_type():
    from sqlalchemy import Integer as _I

    return _I()
