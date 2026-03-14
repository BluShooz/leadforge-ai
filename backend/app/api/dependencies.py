"""
LeadForge AI - API Dependencies
Common dependencies for API routes
"""
from typing import Generator, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_user_id_from_token
from app.core.rate_limit import rate_limit_api


def get_current_user_id(
    user_id: int = Depends(get_user_id_from_token)
) -> int:
    """Get current authenticated user ID"""
    return user_id


def get_current_user_db(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Get current user from database"""
    from app.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


async def rate_limit_check(
    request,
    identifier: Optional[str] = None
):
    """Check API rate limits"""
    await rate_limit_check(request, identifier)


def require_admin(
    current_user = Depends(get_current_user_db)
):
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_organization(
    db: Session = Depends(get_db),
    user = Depends(get_current_user_db)
):
    """Get user's organization"""
    from app.models import Organization
    org = db.query(Organization).filter(
        Organization.user_id == user.id
    ).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return org
