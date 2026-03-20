"""Health check endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test that the health endpoint returns ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
