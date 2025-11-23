# dependencies.py - COMPLETE FIXED VERSION
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
import os

from database import get_database
from utils.security import verify_token
from utils.cookies import get_token_from_cookie, debug_cookie_info
from models.user import User, RoleEnum

# OAuth2 scheme for token endpoint - use this consistently
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login", auto_error=False)

async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db=Depends(get_database)
):
    """
    Enhanced get_current_user with comprehensive debugging for both environments
    """
    from crud.user import UserCRUD
    crud = UserCRUD(db)
    
    environment = os.getenv("ENVIRONMENT", "development")
    
    print(f"🔐 AUTHENTICATION CHECK - Environment: {environment}")
    print(f"🌐 Request origin: {request.headers.get('origin')}")
    
    # Try to get token from Authorization header first
    auth_token = token
    token_source = "Authorization Header"
    
    # If no header token, try to get from cookie
    if not auth_token:
        auth_token = get_token_from_cookie(request)
        token_source = "Cookie"
    
    print(f"🔑 Token source: {token_source}")
    print(f"🔑 Token present: {'YES' if auth_token else 'NO'}")
    
    # Comprehensive cookie debugging
    if not auth_token:
        debug_cookie_info(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token validity
    payload = verify_token(auth_token)
    if not payload:
        print(f"❌ Token verification FAILED")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    role: str = payload.get("role")
    
    if email is None:
        print(f"❌ No email in token payload")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload - missing email",
        )
    
    print(f"✅ Token verified - Email: {email}, Role: {role}")
    
    # Get user from database
    user = await crud.get_user_by_email(email)
    if user is None:
        print(f"❌ User not found in database: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    # Check if user is active
    if not user.is_active:
        print(f"❌ User account deactivated: {email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated. Please contact administrator."
        )
    
    print(f"✅ AUTHENTICATION SUCCESS - User: {user.username} ({user.role})")
    return user

async def require_admin(current_user: User = Depends(get_current_user)):
    """
    Require admin privileges with enhanced debugging
    """
    print(f"🔒 ADMIN CHECK - User: {current_user.username}, Role: {current_user.role}")
    
    if current_user.role != RoleEnum.admin:
        print(f"❌ ADMIN ACCESS DENIED - User role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    print("✅ ADMIN ACCESS GRANTED")
    return current_user

async def require_instructor_or_admin(current_user: User = Depends(get_current_user)):
    """
    Require instructor or admin privileges
    """
    print(f"🔒 INSTRUCTOR/ADMIN CHECK - User: {current_user.username}, Role: {current_user.role}")
    
    if current_user.role not in [RoleEnum.admin, RoleEnum.instructor]:
        print(f"❌ INSTRUCTOR/ADMIN ACCESS DENIED - User role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor or admin privileges required"
        )
    
    print("✅ INSTRUCTOR/ADMIN ACCESS GRANTED")
    return current_user

async def require_student(current_user: User = Depends(get_current_user)):
    """
    Require student privileges
    """
    print(f"🔒 STUDENT CHECK - User: {current_user.username}, Role: {current_user.role}")
    
    if current_user.role != RoleEnum.student:
        print(f"❌ STUDENT ACCESS DENIED - User role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student privileges required"
        )
    
    print("✅ STUDENT ACCESS GRANTED")
    return current_user

async def require_any_user(current_user: User = Depends(get_current_user)):
    """
    Allows any authenticated user (admin, instructor, or student)
    """
    print(f"🔒 ANY USER CHECK - User: {current_user.username}, Role: {current_user.role}")
    print("✅ ANY USER ACCESS GRANTED")
    return current_user

async def require_admin_or_student(current_user: User = Depends(get_current_user)):
    """
    Allows admin and students only
    """
    print(f"🔒 ADMIN/STUDENT CHECK - User: {current_user.username}, Role: {current_user.role}")
    
    if current_user.role not in [RoleEnum.admin, RoleEnum.student]:
        print(f"❌ ADMIN/STUDENT ACCESS DENIED - User role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or student privileges required"
        )
    
    print("✅ ADMIN/STUDENT ACCESS GRANTED")
    return current_user

async def require_admin_or_instructor(current_user: User = Depends(get_current_user)):
    """
    Allows admin and instructors only (excludes students)
    """
    print(f"🔒 ADMIN/INSTRUCTOR CHECK - User: {current_user.username}, Role: {current_user.role}")
    
    if current_user.role not in [RoleEnum.admin, RoleEnum.instructor]:
        print(f"❌ ADMIN/INSTRUCTOR ACCESS DENIED - User role: {current_user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or instructor privileges required"
        )
    
    print("✅ ADMIN/INSTRUCTOR ACCESS GRANTED")
    return current_user

# Additional debugging dependency for development
async def debug_auth(request: Request, db=Depends(get_database)):
    """
    Debug endpoint to check authentication state without requiring auth
    """
    from crud.user import UserCRUD
    crud = UserCRUD(db)
    
    debug_info = {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "request_origin": request.headers.get("origin"),
        "headers": {
            "authorization": request.headers.get("authorization"),
            "cookie": request.headers.get("cookie"),
        },
        "cookies_received": dict(request.cookies),
        "has_access_token": "access_token" in dict(request.cookies),
        "authentication_status": "unknown"
    }
    
    # Try to authenticate to get more info
    try:
        user = await get_current_user(request, None, db)
        debug_info["authentication_status"] = "authenticated"
        debug_info["user"] = {
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active
        }
    except HTTPException as e:
        debug_info["authentication_status"] = f"failed: {e.detail}"
    except Exception as e:
        debug_info["authentication_status"] = f"error: {str(e)}"
    
    return debug_info