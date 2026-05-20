"""
Pytest configuration and fixtures.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from app.main import app
from app.database import Base, get_db
from app.config import settings


# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.database_url.replace("/fameshield", "/fameshield_test")

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_organization(db_session: AsyncSession):
    """Create test organization."""
    from app.models.organization import Organization, OrganizationType, OrganizationTier

    org = Organization(
        name="Test University",
        type=OrganizationType.SCHOOL,
        tier=OrganizationTier.PROFESSIONAL,
        contact_email="test@university.edu"
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def test_user(db_session: AsyncSession, test_organization):
    """Create test admin user."""
    from app.models.user import User, UserRole
    from app.services.auth_service import hash_password

    user = User(
        email="admin@test.com",
        hashed_password=hash_password("testpass123"),
        first_name="Test",
        last_name="Admin",
        role=UserRole.ADMIN,
        organization_id=test_organization.id,
        permissions=["*"]
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_athlete(db_session: AsyncSession, test_organization):
    """Create test athlete."""
    from app.models.athlete import Athlete, RiskLevel

    athlete = Athlete(
        organization_id=test_organization.id,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@test.com",
        sport="Soccer",
        date_of_birth="2005-01-15",
        risk_level=RiskLevel.MEDIUM,
        monitoring_enabled=True
    )
    db_session.add(athlete)
    await db_session.commit()
    await db_session.refresh(athlete)
    return athlete


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user) -> dict:
    """Get authentication headers for test user."""
    from app.services.auth_service import create_access_token

    token = create_access_token({"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}
