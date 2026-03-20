"""Role-Based Access Control (RBAC) middleware."""

from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException, status

from nexus.api.routes.auth import get_current_user

ROLE_HIERARCHY = {"admin": 3, "analyst": 2, "viewer": 1}


def require_role(*allowed_roles: str):
    """FastAPI dependency factory that checks the current user's role.

    Usage:
        @router.post("/something", dependencies=[Depends(require_role("admin", "analyst"))])
        async def do_something(): ...

    Or as a parameter dependency:
        async def do_something(user=Depends(require_role("analyst"))): ...
    """

    async def _check_role(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Required: {', '.join(allowed_roles)}",
            )
        return current_user

    return _check_role


# Convenience shortcuts
require_admin = require_role("admin")
require_analyst = require_role("admin", "analyst")
require_viewer = require_role("admin", "analyst", "viewer")
