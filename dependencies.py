# dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from database import get_database
from utils.security import verify_token
from models.user import User, RoleEnum

# OAuth2 scheme for token endpoint - use this consistently
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_database)
):
    from crud.user import UserCRUD
    crud = UserCRUD(db)
    
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    user = await crud.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

async def require_instructor_or_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in [RoleEnum.admin, RoleEnum.instructor]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor or admin privileges required"
        )
    return current_user

async def require_student(current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student privileges required"
        )
    return current_user

async def require_any_user(current_user: User = Depends(get_current_user)):
    """Allows any authenticated user (admin, instructor, or student)"""
    return current_user

async def require_admin_or_student(current_user: User = Depends(get_current_user)):
    """Allows admin and students only"""
    if current_user.role not in [RoleEnum.admin, RoleEnum.student]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or student privileges required"
        )
    return current_user