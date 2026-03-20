"""Entity endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_search_entities_empty(client):
    """Test searching entities returns empty list when no data."""
    response = await client.get("/api/v1/entities")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_entity_not_found(client):
    """Test getting a non-existent entity returns 404."""
    response = await client.get("/api/v1/entities/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_entity(client, mock_neo4j_driver):
    """Test creating an entity."""
    # Mock the write response
    session = mock_neo4j_driver.session.return_value
    session.__aenter__.return_value = session
    result = session.execute_write.return_value = []

    response = await client.post(
        "/api/v1/entities",
        json={
            "name": "Test Person",
            "type": "Person",
            "confidence": 0.85,
            "source_int": "CYBINT",
            "risk_score": 5.0,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Person"
    assert data["type"] == "Person"
    assert data["confidence"] == 0.85
