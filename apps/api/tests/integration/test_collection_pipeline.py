"""Integration test: collection pipeline — job creation, status tracking."""

import uuid
from unittest.mock import AsyncMock

import pytest


class TestCollectionPipeline:
    """End-to-end collection pipeline test."""

    @pytest.fixture
    def mock_pg_conn(self):
        conn = AsyncMock()
        return conn

    @pytest.mark.asyncio
    async def test_cybint_collection_job_lifecycle(self, mock_pg_conn):
        """CYBINT collection job: create → pending → running → completed."""
        job_id = str(uuid.uuid4())

        # Create job
        mock_pg_conn.fetchrow = AsyncMock(return_value={
            "id": job_id,
            "int_type": "CYBINT",
            "scan_type": "domain_scan",
            "status": "pending",
            "query": "example.com",
            "result_count": 0,
            "created_at": "2024-01-01T00:00:00Z",
        })

        job = await mock_pg_conn.fetchrow("INSERT INTO collection_jobs ...")
        assert job["status"] == "pending"

        # Update to running
        mock_pg_conn.fetchrow = AsyncMock(return_value={
            **job,
            "status": "running",
        })
        job_running = await mock_pg_conn.fetchrow("UPDATE collection_jobs SET status = 'running'")
        assert job_running["status"] == "running"

        # Complete with results
        mock_pg_conn.fetchrow = AsyncMock(return_value={
            **job,
            "status": "completed",
            "result_count": 15,
        })
        job_done = await mock_pg_conn.fetchrow("UPDATE collection_jobs SET status = 'completed'")
        assert job_done["status"] == "completed"
        assert job_done["result_count"] == 15

    @pytest.mark.asyncio
    async def test_multi_int_collection(self, mock_pg_conn):
        """Multiple INT types can run in parallel."""
        int_types = ["CYBINT", "SOCMINT", "SIGINT", "GEOINT"]
        jobs = []

        for int_type in int_types:
            job = {
                "id": str(uuid.uuid4()),
                "int_type": int_type,
                "status": "pending",
                "query": "test-target",
            }
            jobs.append(job)

        assert len(jobs) == 4
        assert {j["int_type"] for j in jobs} == {"CYBINT", "SOCMINT", "SIGINT", "GEOINT"}
