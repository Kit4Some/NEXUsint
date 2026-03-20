"""Collection endpoint tests."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime


@pytest.mark.asyncio
async def test_create_cybint_job(client, mock_pg_pool):
    """Test creating a CYBINT collection job."""
    job_id = uuid4()
    conn = mock_pg_pool.acquire.return_value
    conn.__aenter__.return_value = conn
    conn.fetchrow = AsyncMock(
        return_value={
            "id": job_id,
            "int_type": "CYBINT",
            "query": "example.com",
            "scan_type": "dns",
            "status": "queued",
            "progress": 0,
            "result_count": 0,
            "error": None,
            "created_at": datetime.utcnow(),
            "completed_at": None,
        }
    )

    response = await client.post(
        "/api/v1/collect/cybint",
        json={"query": "example.com", "scan_type": "dns"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["int_type"] == "CYBINT"
    assert data["query"] == "example.com"
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_get_collection_status_not_found(client, mock_pg_pool):
    """Test getting status of non-existent collection job."""
    conn = mock_pg_pool.acquire.return_value
    conn.__aenter__.return_value = conn
    conn.fetchrow = AsyncMock(return_value=None)

    response = await client.get(f"/api/v1/collect/status/{uuid4()}")
    assert response.status_code == 404
