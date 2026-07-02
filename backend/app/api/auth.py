"""
Authentication API endpoints.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.services.auth_service import AuthService
from app.services.password_reset_service import (
    consume_token,
    create_reset_token,
    send_reset_email,
)


router = APIRouter(prefix="/auth", tags=["authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Pydantic schemas
class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request schema."""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class AcceptedResponse(BaseModel):
    status: str = "accepted"


class UserRegister(BaseModel):
    """User registration schema."""
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    organization_name: str
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    organization_id: UUID
    permissions: list[str]
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


# Dependency for getting current user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = await AuthService.get_current_user(db, token)

    if user is None:
        raise credentials_exception

    return user


# Dependency for checking permissions
def require_permission(permission: str):
    """Dependency factory for permission checking."""
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not AuthService.check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        return current_user
    return permission_checker


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user and organization.

    Creates both an organization and an admin user.
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Join an existing org by name when there's exactly one match; otherwise
    # create a new one. This treats "FameShield Self-Serve" (and any other
    # org an admin has already set up) as reusable, so staff signups don't
    # spawn duplicate orgs with the same name.
    result = await db.execute(
        select(Organization).where(Organization.name == user_data.organization_name)
    )
    existing_orgs = list(result.scalars().all())
    if len(existing_orgs) == 1:
        organization = existing_orgs[0]
    else:
        organization = Organization(
            name=user_data.organization_name,
            type="individual",
            tier="starter",
        )
        db.add(organization)
        await db.flush()

    # Create admin user
    hashed_password = AuthService.hash_password(user_data.password)
    user = User(
        organization_id=organization.id,
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        role=UserRole.ADMIN,
        permissions=AuthService.get_role_permissions(UserRole.ADMIN)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login.

    Returns access token and refresh token.
    """
    user = await AuthService.authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    refresh_token = AuthService.create_refresh_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    payload = AuthService.decode_token(token_data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Create new tokens
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    new_refresh_token = AuthService.create_refresh_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    """
    return current_user


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout (client should discard tokens).
    """
    return {"message": "Successfully logged out"}


@router.post(
    "/forgot-password",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(
    payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Accept the request unconditionally to avoid leaking whether an email exists."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user:
        raw, _ = await create_reset_token(db, user.id, "staff")
        await db.commit()
        send_reset_email(user.email, user.first_name, raw, "staff")
    return AcceptedResponse()


@router.post("/reset-password", response_model=Token)
async def reset_password(
    payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )
    subject_id = await consume_token(db, payload.token, "staff")
    if not subject_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link is invalid or expired",
        )
    result = await db.execute(select(User).where(User.id == subject_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account no longer exists"
        )
    user.hashed_password = AuthService.hash_password(payload.new_password)
    user.last_login_at = datetime.utcnow()
    await db.commit()
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    refresh_token_val = AuthService.create_refresh_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token_val,
        "token_type": "bearer",
    }
