"""
Authentication service for JWT token management and password hashing.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User, UserRole


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Role-based permissions mapping
ROLE_PERMISSIONS: Dict[UserRole, list[str]] = {
    UserRole.ADMIN: ["*"],  # All permissions
    UserRole.COACH: [
        "view_athletes",
        "view_content",
        "create_takedown",
        "view_escalations",
    ],
    UserRole.AGENT: [
        "view_athletes",
        "view_content",
        "create_takedown",
    ],
    UserRole.MENTAL_HEALTH_STAFF: [
        "view_escalations",
        "update_escalations",
    ],
    UserRole.LEGAL: [
        "view_takedown",
        "update_takedown",
        "view_evidence",
    ],
    UserRole.VIEWER: [
        "view_athletes",
        "view_content",
    ],
}


class AuthService:
    """Service for authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain text password."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.jwt_access_token_expire_minutes
            )

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)

        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and verify a JWT token."""
        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """Authenticate a user by email and password."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not AuthService.verify_password(password, user.hashed_password):
            return None

        # Update last login
        user.last_login_at = datetime.utcnow()
        await db.commit()

        return user

    @staticmethod
    async def get_current_user(db: AsyncSession, token: str) -> Optional[User]:
        """Get the current user from a JWT token."""
        payload = AuthService.decode_token(token)

        if not payload:
            return None

        user_id: str = payload.get("sub")
        if not user_id:
            return None

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        return user

    @staticmethod
    def get_role_permissions(role: UserRole) -> list[str]:
        """Get default permissions for a role."""
        return ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    def check_permission(user: User, permission: str) -> bool:
        """Check if a user has a specific permission."""
        # Admin has all permissions
        if user.role == UserRole.ADMIN:
            return True

        # Check explicit permissions
        if permission in user.permissions:
            return True

        # Check role-based permissions
        role_perms = ROLE_PERMISSIONS.get(user.role, [])
        return permission in role_perms or "*" in role_perms
