from fastapi import Response
from datetime import timedelta
import os

def set_auth_cookie(response: Response, token: str, expires_days: int = 7):
    """
    Set HTTP-only authentication cookie - UPDATED FOR DEVELOPMENT
    """
    expires = timedelta(days=expires_days)
    
    # DEVELOPMENT-FRIENDLY SETTINGS
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,      # Still HTTP-only for security
        secure=False,       # False for HTTP development
        samesite="lax",     # 'lax' works better than 'none' for localhost
        max_age=int(expires.total_seconds()),
        path="/",           # Available on all paths
        domain=None         # No domain restriction for localhost
    )
    print(f"🍪 Cookie SET: access_token (length: {len(token)})")
    print(f"🍪 Cookie settings: secure=False, samesite=lax, path=/")

def delete_auth_cookie(response: Response):
    """
    Delete authentication cookie (logout) - UPDATED
    """
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=None
    )
    print("🍪 Cookie deleted: access_token")

def get_token_from_cookie(request) -> str:
    """
    Extract token from cookie - ENHANCED DEBUGGING
    """
    all_cookies = dict(request.cookies)
    token = request.cookies.get("access_token")
    
    print(f"🍪 All cookies received: {all_cookies}")
    print(f"🍪 Access token retrieved: {'YES' if token else 'NO'}")
    
    # Detailed debugging
    if not all_cookies:
        print("❌ NO COOKIES RECEIVED AT ALL")
        print("🔍 Possible issues:")
        print("   - CORS not configured properly")
        print("   - Frontend not sending credentials")
        print("   - Domain/path mismatch")
    elif "access_token" not in all_cookies:
        print("❌ access_token cookie missing")
        print(f"🔍 Available cookies: {list(all_cookies.keys())}")
    
    return token