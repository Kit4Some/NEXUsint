"""SOCMINT routes — social media intelligence and cross-platform search."""

from pydantic import BaseModel

from fastapi import APIRouter

from nexus.collectors.socmint.cross_platform_resolver import CrossPlatformResolver
from nexus.collectors.socmint.manager import SocmintManager
from nexus.collectors.base import CollectionQuery

router = APIRouter()


class UsernameSearchRequest(BaseModel):
    username: str
    platforms: list[str] | None = None


@router.post("/username-search")
async def username_search(request: UsernameSearchRequest):
    """Search for a username across multiple social media platforms."""
    resolver = CrossPlatformResolver()
    try:
        results = await resolver.collect(CollectionQuery(
            query=request.username,
            scan_type="username_search",
            options={"platforms": request.platforms} if request.platforms else {},
        ))
        return {
            "username": request.username,
            "profiles": [r.normalized for r in results],
            "found_count": len(results),
        }
    finally:
        await resolver.close()


@router.get("/social-accounts/{username}")
async def get_social_accounts(username: str):
    """Get aggregated social media profiles for a username."""
    resolver = CrossPlatformResolver()
    try:
        results = await resolver.collect(CollectionQuery(
            query=username, scan_type="username_search",
        ))
        return {
            "username": username,
            "accounts": [r.normalized for r in results],
            "platform_count": len(results),
        }
    finally:
        await resolver.close()


@router.post("/search")
async def socmint_search(
    query: str,
    scan_type: str = "keyword_search",
):
    """Search social media via SOCMINT collectors."""
    mgr = SocmintManager()
    try:
        results = await mgr.collect(query, scan_type=scan_type)
        return {
            "query": query,
            "scan_type": scan_type,
            "results": [r.normalized for r in results],
            "count": len(results),
        }
    finally:
        await mgr.close()
