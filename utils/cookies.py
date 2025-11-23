# utils/cookies.py - COMPLETE FIXED VERSION
from fastapi import Response, Request
from datetime import timedelta
import os

def get_cookie_settings():
    """
    Get cookie settings based on environment - FIXED FOR RENDER
    """
    environment = os.getenv("ENVIRONMENT", "development")
    
    print(f"🔧 Cookie Environment: {environment}")
    
    if environment == "production":
        # PRODUCTION SETTINGS (Render)
        settings = {
            "httponly": True,
            "secure": True,           # True for HTTPS
            "samesite": "none",       # Critical for cross-domain
            "domain": ".onrender.com", # Allow all subdomains
            "path": "/"
        }
        print("🍪 Using PRODUCTION cookie settings (secure=true, samesite=none)")
    else:
        # DEVELOPMENT SETTINGS (localhost)
        settings = {
            "httponly": True,
            "secure": False,          # False for HTTP
            "samesite": "lax",        # Works for localhost
            "domain": None,           # No domain restriction
            "path": "/"
        }
        print("🍪 Using DEVELOPMENT cookie settings (secure=false, samesite=lax)")
    
    return settings

def set_auth_cookie(response: Response, token: str, expires_days: int = 7):
    """
    Set HTTP-only authentication cookie - FIXED FOR BOTH ENVIRONMENTS
    """
    expires = timedelta(days=expires_days)
    settings = get_cookie_settings()
    
    # Set the main access_token cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=settings["httponly"],
        secure=settings["secure"],
        samesite=settings["samesite"],
        domain=settings["domain"],
        max_age=int(expires.total_seconds()),
        path=settings["path"]
    )
    
    # Set a debug cookie in development (non-http-only)
    if os.getenv("ENVIRONMENT") != "production":
        response.set_cookie(
            key="debug_token",
            value=token[:20] + "...",  # Partial token for debugging
            httponly=False,
            secure=False,
            samesite="lax",
            max_age=int(expires.total_seconds()),
            path="/"
        )
        print(f"🔍 Debug cookie set: debug_token={token[:20]}...")
    
    print(f"✅ Cookie SET: access_token (length: {len(token)})")
    print(f"🔧 Cookie settings: secure={settings['secure']}, samesite={settings['samesite']}, domain={settings['domain']}")

def delete_auth_cookie(response: Response):
    """
    Delete authentication cookie (logout) - FIXED FOR BOTH ENVIRONMENTS
    """
    settings = get_cookie_settings()
    
    # Delete main access_token cookie
    response.delete_cookie(
        key="access_token",
        path=settings["path"],
        domain=settings["domain"]
    )
    
    # Delete debug cookie in development
    if os.getenv("ENVIRONMENT") != "production":
        response.delete_cookie(
            key="debug_token",
            path="/"
        )
    
    print(f"✅ Cookie DELETED: access_token")
    print(f"🔧 Deletion settings: domain={settings['domain']}")

def get_token_from_cookie(request: Request) -> str:
    """
    Extract token from cookie - ENHANCED DEBUGGING FOR BOTH ENVIRONMENTS
    """
    all_cookies = dict(request.cookies)
    token = request.cookies.get("access_token")
    
    environment = os.getenv("ENVIRONMENT", "development")
    
    print(f"🍪 Environment: {environment}")
    print(f"🍪 All cookies received: {all_cookies}")
    print(f"🍪 Access token present: {'YES' if token else 'NO'}")
    
    # Detailed debugging
    if not all_cookies:
        print("❌ NO COOKIES RECEIVED AT ALL")
        print("🔍 Possible issues:")
        print("   - CORS not configured properly")
        print("   - Frontend not sending credentials (missing credentials: 'include')")
        print("   - Domain/path mismatch")
        print("   - Browser blocking cross-site cookies")
    elif "access_token" not in all_cookies:
        print("❌ access_token cookie missing")
        print(f"🔍 Available cookies: {list(all_cookies.keys())}")
        
        # Check for debug token in development
        if "debug_token" in all_cookies and environment != "production":
            print("🔍 Debug token found (development mode)")
    
    # Additional debug info for production
    if environment == "production":
        origin = request.headers.get("origin")
        print(f"🌐 Request origin: {origin}")
        print(f"🔒 Secure context: {request.url.scheme}")
        
        # Check if we're dealing with cross-site request
        if origin and "onrender.com" in origin:
            expected_domain = ".onrender.com"
            print(f"🎯 Expected cookie domain: {expected_domain}")
    
    return token

def debug_cookie_info(request: Request):
    """
    Comprehensive cookie debugging information - ADDED MISSING FUNCTION
    """
    all_cookies = dict(request.cookies)
    headers = dict(request.headers)
    
    debug_info = {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "cookies_received": all_cookies,
        "has_access_token": "access_token" in all_cookies,
        "request_origin": headers.get("origin"),
        "user_agent": headers.get("user-agent"),
        "cookie_header": headers.get("cookie"),
        "url_scheme": request.url.scheme
    }
    
    print("🔍 COOKIE DEBUG INFO:")
    for key, value in debug_info.items():
        print(f"   {key}: {value}")
    
    return debug_info