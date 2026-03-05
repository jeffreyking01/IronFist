"""
Auth dependencies — import these in route handlers to protect endpoints.

Usage:
    from app.auth.dependencies import require_auth, require_admin

    @router.get("/protected")
    async def protected(user: TokenData = Depends(require_auth)):
        return {"user": user.username}

    @router.delete("/admin-only")
    async def admin_only(user: TokenData = Depends(require_admin)):
        ...
"""

from fastapi import Depends, HTTPException, status
from app.auth.auth import get_current_user, TokenData


async def require_auth(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Any authenticated user."""
    return current_user


async def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Admin role only."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


async def require_analyst(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Analyst or admin role."""
    if current_user.role not in ("analyst", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst role or higher required",
        )
    return current_user
