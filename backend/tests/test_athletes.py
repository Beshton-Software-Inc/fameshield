"""
Test athlete endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_athlete(client: AsyncClient, auth_headers):
    """Test creating an athlete."""
    response = await client.post(
        "/api/v1/athletes",
        headers=auth_headers,
        json={
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@test.com",
            "sport": "Basketball",
            "date_of_birth": "2004-05-20",
            "risk_level": "medium"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Smith"
    assert data["sport"] == "Basketball"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_athletes(client: AsyncClient, auth_headers, test_athlete):
    """Test listing athletes."""
    response = await client.get(
        "/api/v1/athletes",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(a["id"] == str(test_athlete.id) for a in data)


@pytest.mark.asyncio
async def test_get_athlete(client: AsyncClient, auth_headers, test_athlete):
    """Test getting athlete details."""
    response = await client.get(
        f"/api/v1/athletes/{test_athlete.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_athlete.id)
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"


@pytest.mark.asyncio
async def test_update_athlete(client: AsyncClient, auth_headers, test_athlete):
    """Test updating athlete."""
    response = await client.patch(
        f"/api/v1/athletes/{test_athlete.id}",
        headers=auth_headers,
        json={
            "risk_level": "high"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "high"


@pytest.mark.asyncio
async def test_delete_athlete(client: AsyncClient, auth_headers, test_athlete):
    """Test deleting athlete."""
    response = await client.delete(
        f"/api/v1/athletes/{test_athlete.id}",
        headers=auth_headers
    )
    assert response.status_code == 200

    # Verify deletion
    response = await client.get(
        f"/api/v1/athletes/{test_athlete.id}",
        headers=auth_headers
    )
    assert response.status_code == 404
