"""REST endpoints for news feed configuration and retrieval."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from nexus.models.news import NewsFeedConfig
from nexus.services.live_store import get_live_data

router = APIRouter()


@router.get("/latest")
async def get_latest_news() -> list[dict[str, Any]]:
    """Return the latest news articles from the live data store."""
    news = await get_live_data("news")
    return news or []


@router.get("/feeds")
async def get_feeds() -> list[dict[str, Any]]:
    """Return the current RSS feed configuration."""
    from nexus.services.news_feed_config import get_feeds

    return get_feeds()


@router.put("/feeds")
async def update_feeds(feeds: list[NewsFeedConfig]) -> dict[str, str]:
    """Update the RSS feed configuration."""
    from nexus.services.news_feed_config import save_feeds

    if len(feeds) > 25:
        raise HTTPException(status_code=400, detail="Maximum 25 feeds allowed")
    if len(feeds) == 0:
        raise HTTPException(status_code=400, detail="At least one feed required")

    save_feeds([f.model_dump() for f in feeds])
    return {"status": "saved", "count": str(len(feeds))}


@router.post("/feeds/reset")
async def reset_feeds() -> dict[str, str]:
    """Reset RSS feeds to defaults."""
    from nexus.services.news_feed_config import reset_feeds

    reset_feeds()
    return {"status": "reset"}
