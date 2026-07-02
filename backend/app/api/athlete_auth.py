"""Athlete self-serve authentication endpoints (signup, login, refresh, me)."""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.models.athlete import Athlete
from app.models.organization import Organization, OrganizationTier, OrganizationType
from app.services.auth_service import AuthService
from app.services.password_reset_service import (
    consume_token,
    create_reset_token,
    send_reset_email,
)

SELF_SERVE_ORG_NAME = "FameShield Self-Serve"


async def _get_or_create_self_serve_org(db: AsyncSession) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.name == SELF_SERVE_ORG_NAME)
    )
    org = result.scalar_one_or_none()
    if org:
        return org
    org = Organization(
        name=SELF_SERVE_ORG_NAME,
        type=OrganizationType.INDIVIDUAL,
        tier=OrganizationTier.STARTER,
    )
    db.add(org)
    await db.flush()
    return org

router = APIRouter(prefix="/athlete-auth", tags=["athlete-auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/athlete-auth/login", auto_error=False)

ATHLETE_SUBJECT = "athlete"


class AthleteRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    date_of_birth: date
    sport: str
    phone: Optional[str] = None


class AthleteLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    athlete_id: UUID


class AthleteRefresh(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class AcceptedResponse(BaseModel):
    status: str = "accepted"


def _make_tokens(athlete: Athlete) -> AthleteLoginResponse:
    now = datetime.utcnow()
    access = jwt.encode(
        {
            "sub": str(athlete.id),
            "email": athlete.email,
            "kind": ATHLETE_SUBJECT,
            "type": "access",
            "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    refresh = jwt.encode(
        {
            "sub": str(athlete.id),
            "kind": ATHLETE_SUBJECT,
            "type": "refresh",
            "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return AthleteLoginResponse(
        access_token=access, refresh_token=refresh, athlete_id=athlete.id
    )


async def get_current_athlete(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Athlete:
    """Resolve the calling athlete from the bearer token, or raise 401."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Athlete authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise exc
    payload = AuthService.decode_token(token)
    if not payload or payload.get("kind") != ATHLETE_SUBJECT or payload.get("type") != "access":
        raise exc
    athlete_id = payload.get("sub")
    if not athlete_id:
        raise exc
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise exc
    return athlete


@router.post("/register", response_model=AthleteLoginResponse, status_code=status.HTTP_201_CREATED)
async def register_athlete(payload: AthleteRegister, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Athlete).where(Athlete.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    org = await _get_or_create_self_serve_org(db)
    athlete = Athlete(
        organization_id=org.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        hashed_password=AuthService.hash_password(payload.password),
        date_of_birth=payload.date_of_birth,
        sport=payload.sport,
        phone=payload.phone,
        monitoring_enabled=True,
    )
    db.add(athlete)
    await db.commit()
    await db.refresh(athlete)
    return _make_tokens(athlete)


@router.post("/login", response_model=AthleteLoginResponse)
async def login_athlete(
    form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Athlete).where(Athlete.email == form.username))
    athlete = result.scalar_one_or_none()
    if (
        not athlete
        or not athlete.hashed_password
        or not AuthService.verify_password(form.password, athlete.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )
    athlete.last_login_at = datetime.utcnow()
    await db.commit()
    return _make_tokens(athlete)


@router.post(
    "/forgot-password",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def athlete_forgot_password(
    payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Accept the request unconditionally to avoid leaking whether an email exists."""
    result = await db.execute(select(Athlete).where(Athlete.email == payload.email))
    athlete = result.scalar_one_or_none()
    if athlete:
        raw, _ = await create_reset_token(db, athlete.id, "athlete")
        await db.commit()
        send_reset_email(athlete.email, athlete.first_name, raw, "athlete")
    return AcceptedResponse()


@router.post("/reset-password", response_model=AthleteLoginResponse)
async def athlete_reset_password(
    payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )
    subject_id = await consume_token(db, payload.token, "athlete")
    if not subject_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or expired",
        )
    result = await db.execute(select(Athlete).where(Athlete.id == subject_id))
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account no longer exists"
        )
    athlete.hashed_password = AuthService.hash_password(payload.new_password)
    athlete.last_login_at = datetime.utcnow()
    await db.commit()
    return _make_tokens(athlete)


@router.post("/refresh", response_model=AthleteLoginResponse)
async def refresh_athlete_token(payload: AthleteRefresh, db: AsyncSession = Depends(get_db)):
    decoded = AuthService.decode_token(payload.refresh_token)
    if not decoded or decoded.get("kind") != ATHLETE_SUBJECT or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    result = await db.execute(select(Athlete).where(Athlete.id == decoded.get("sub")))
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Athlete not found"
        )
    return _make_tokens(athlete)
