from fastapi import Response
from datetime import timedelta
import os

def set_auth_cookie(response: Response, token: str, expires_days: int = 7):
    """
    Set HTTP-only authentication cookie
    """
    expires = timedelta(days=expires_days)
    
    # Determine if we're in production
    is_production = os.getenv("RENDER", False) or os.getenv("ENVIRONMENT") == "production"
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=is_production,  # True in production, False in development
        samesite="lax",
        max_age=int(expires.total_seconds()),
        path="/",
        domain=None  # Let browser handle domain
    )

def delete_auth_cookie(response: Response):
    """
    Delete authentication cookie (logout)
    """
    response.delete_cookie(
        key="access_token",
        path="/"
    )

def get_token_from_cookie(request) -> str:
    """
    Extract token from cookie
    """
    return request.cookies.get("access_token")