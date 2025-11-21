# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from datetime import datetime
import os, uuid
from bson import ObjectId

from database import get_database
from models.user import User, RoleEnum
from schemas.user import UserOut, UserCreate, AdminUserCreate
from utils.security import hash_password, verify_password, create_access_token
from dependencies import get_current_user, require_admin, oauth2_scheme

# Create directory if not exists
UPLOAD_DIR = "static/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/users", tags=["Users"])

async def get_user_crud(db=Depends(get_database)):
    from crud.user import UserCRUD
    return UserCRUD(db)

# routers/users.py - Update the signup function
@router.post("/signup", response_model=UserOut)
async def signup(
    full_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    date_of_birth: str = Form(...),
    phone_number: str = Form(...),
    gender: str = Form(...),
    bio: str = Form(None),
    file: UploadFile = File(None),
    crud = Depends(get_user_crud)
):

    print("✅ SIGNUP ENDPOINT HIT!")
    # Confirm password match
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Handle avatar upload
    avatar_url = None
    if file:
        allowed_exts = [".jpg", ".jpeg", ".png"]
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="Only .jpg, .jpeg, .png allowed")

        filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        avatar_url = f"/static/avatars/{filename}"

    # Check if user already exists
    existing_email = await crud.get_user_by_email(email.lower())
    existing_username = await crud.get_user_by_username(username)
    if existing_email or existing_username:
        raise HTTPException(status_code=400, detail="Email or username already registered")

    # Create UserCreate object with proper enum value
    user_data = UserCreate(
        full_name=full_name,
        username=username,
        email=email.lower(),
        password=password,
        role=RoleEnum.student,  # This should be the enum value, not string
        date_of_birth=date_of_birth,
        phone_number=phone_number,
        gender=gender.lower() if gender else None,
        bio=bio
    )

    # Create user using the existing create_user method
    user = await crud.create_user(user_data, avatar_url=avatar_url)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    print(f"✅ User Created Successfully: {user.username} ({user.email})")
    
    return user

# Login endpoint - No authentication required
@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    crud = Depends(get_user_crud)
):
    identifier = form_data.username.strip()
    print(f"🔍 Login attempt with identifier: '{identifier}'")

    # Find user by email OR username
    user = await crud.get_user_by_identifier(identifier)
    
    if user:
        print(f"✅ User found: {user.username} ({user.email})")
        print(f"🔐 Password hash type: {user.password_hash[:10]}...")  # Debug hash format
    else:
        print(f"❌ User not found for identifier: '{identifier}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Verify password using bcrypt with proper truncation
    password_verified = False
    try:
        # Import bcrypt directly
        import bcrypt as bcrypt_lib
        
        # Convert password to bytes and truncate properly
        password_bytes = form_data.password.encode('utf-8')
        if len(password_bytes) > 72:
            print(f"⚠️ Password too long ({len(password_bytes)} bytes), truncating to 72 bytes")
            password_bytes = password_bytes[:72]
        
        # Convert the stored hash from string to bytes
        stored_hash_bytes = user.password_hash.encode('utf-8')
        
        # Verify using bcrypt library directly (bypass passlib issues)
        password_verified = bcrypt_lib.checkpw(password_bytes, stored_hash_bytes)
        print(f"🔑 Password verification result: {password_verified}")
        
    except Exception as e:
        print(f"❌ Password verification error: {str(e)}")
        # Fallback: try the original verify_password function
        try:
            from utils.security import verify_password
            # Make sure the password is truncated for the fallback
            truncated_password = form_data.password
            if len(truncated_password.encode('utf-8')) > 72:
                truncated_password = truncated_password[:72]
            password_verified = verify_password(truncated_password, user.password_hash)
            print(f"🔑 Fallback verification result: {password_verified}")
        except Exception as fallback_error:
            print(f"❌ Fallback verification also failed: {fallback_error}")
            password_verified = False

    if not password_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
        
    # Ensure user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is deactivated. Contact admin."
        )

    # Update last login
    await crud.update_last_login(user.id)

    # Create token including role
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active
        }
    }

# --- Get current user ---
@router.get("/me", response_model=UserOut)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

# --- Update own profile (Users can update their own profile) ---
@router.put("/me", response_model=UserOut)
async def update_own_profile(
    full_name: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    file: UploadFile = File(None),
    crud = Depends(get_user_crud),
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's own profile
    """
    update_data = {}
    
    # Basic profile fields that users can update
    if full_name is not None: 
        update_data["full_name"] = full_name
    if username is not None: 
        update_data["username"] = username
    if email is not None: 
        update_data["email"] = email.lower()
    if date_of_birth is not None: 
        update_data["date_of_birth"] = date_of_birth
    if phone_number is not None: 
        update_data["phone_number"] = phone_number
    if gender is not None: 
        update_data["gender"] = gender.lower()
    if bio is not None: 
        update_data["bio"] = bio
    if password: 
        update_data["password_hash"] = hash_password(password)

    # Handle avatar upload
    if file:
        allowed_exts = [".jpg", ".jpeg", ".png"]
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="Only .jpg, .jpeg, .png allowed")

        filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        update_data["avatar_url"] = f"/static/avatars/{filename}"

    # Update the user
    updated_user = await crud.update_user(str(current_user.id), update_data)
    if not updated_user:
        raise HTTPException(status_code=400, detail="Username or email already taken")
    
    return updated_user

# --- Admin update any user's profile ---
@router.put("/admin/update/{user_id}", response_model=UserOut)
async def admin_update_user(
    user_id: str,
    full_name: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    role: Optional[RoleEnum] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    file: UploadFile = File(None),
    crud = Depends(get_user_crud),
    current_admin: User = Depends(require_admin)
):
    """
    Admin update any user's profile (includes role and status changes)
    """
    # Check if user exists
    existing_user = await crud.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {}
    
    # All fields that admin can update
    if full_name is not None: 
        update_data["full_name"] = full_name
    if username is not None: 
        update_data["username"] = username
    if email is not None: 
        update_data["email"] = email.lower()
    if role is not None: 
        update_data["role"] = role
    if date_of_birth is not None: 
        update_data["date_of_birth"] = date_of_birth
    if phone_number is not None: 
        update_data["phone_number"] = phone_number
    if gender is not None: 
        update_data["gender"] = gender.lower()
    if bio is not None: 
        update_data["bio"] = bio
    if password: 
        update_data["password_hash"] = hash_password(password)
    if is_active is not None: 
        update_data["is_active"] = is_active

    # Handle avatar upload
    if file:
        allowed_exts = [".jpg", ".jpeg", ".png"]
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail="Only .jpg, .jpeg, .png allowed")

        filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        update_data["avatar_url"] = f"/static/avatars/{filename}"

    # Update the user
    updated_user = await crud.update_user(user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=400, detail="Username or email already taken")
    
    return updated_user

@router.post("/admin/create", response_model=UserOut)
async def admin_create_user(
    full_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: RoleEnum = Form(...),
    date_of_birth: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    is_active: bool = Form(True),
    crud = Depends(get_user_crud),  # Remove file parameter
    current_admin: User = Depends(require_admin)
):
    # Convert empty strings to None for optional fields
    def clean_optional_field(value: Optional[str]) -> Optional[str]:
        return value if value and value.strip() != "" else None

    # Create user data WITHOUT avatar
    user_data = AdminUserCreate(
        full_name=full_name,
        username=username,
        email=email.lower(),
        password=password,
        role=role,
        date_of_birth=clean_optional_field(date_of_birth),
        phone_number=clean_optional_field(phone_number),
        gender=clean_optional_field(gender),
        bio=clean_optional_field(bio),
        is_active=is_active
    )

    user = await crud.create_user(user_data, avatar_url=None, invited_by=str(current_admin.id))
    if not user:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    return user

# Alternative: Update the existing endpoint to resolve inviter names
@router.get("/admin/all-users", response_model=List[UserOut])
async def get_all_users(
    crud = Depends(get_user_crud),
    current_admin: User = Depends(require_admin)
):
    """
    Get all users with complete information (admin only)
    """
    users = await crud.get_users()
    
    # Resolve inviter names for each user
    for user in users:
        if user.invited_by and user.invited_by != '—':
            inviter_username = await crud.get_inviter_username(user.invited_by)
            if inviter_username:
                user.invited_by = inviter_username
            else:
                user.invited_by = "—"  # Show dash if no inviter found
    
    return users

# --- List users (admin only) ---
@router.get("/admin/list", response_model=List[UserOut])
async def list_users(
    role: Optional[RoleEnum] = None,
    crud = Depends(get_user_crud),
    current_admin: User = Depends(require_admin)
):
    return await crud.get_users(role=role)

# routers/users.py - Add this endpoint
@router.get("/admin/users-status", response_model=List[UserOut])
async def get_users_by_status(
    status: Optional[str] = None,  # "active", "inactive", or None for all
    role: Optional[RoleEnum] = None,
    crud = Depends(get_user_crud),
    current_admin: User = Depends(require_admin)
):
    """
    Get users filtered by active/inactive status (admin only)
    - status: "active" for active users, "inactive" for inactive users, or None for all
    - role: Optional role filter
    """
    # Get all users first
    users = await crud.get_users(role=role)
    
    # Filter by status if specified
    if status == "active":
        users = [user for user in users if user.is_active]
    elif status == "inactive":
        users = [user for user in users if not user.is_active]
    # If status is None or any other value, return all users
    
    # Resolve inviter names for each user
    for user in users:
        if user.invited_by and user.invited_by != '—':
            inviter_username = await crud.get_inviter_username(user.invited_by)
            if inviter_username:
                user.invited_by = inviter_username
            else:
                user.invited_by = "—"
    
    return users

# --- Admin operations ---
@router.put("/admin/deactivate/{user_id}", response_model=UserOut)
async def deactivate_user(
    user_id: str, 
    crud = Depends(get_user_crud), 
    current_admin: User = Depends(require_admin)
):
    user = await crud.update_user(user_id, {"is_active": False})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/admin/reactivate/{user_id}", response_model=UserOut)
async def reactivate_user(
    user_id: str, 
    crud = Depends(get_user_crud), 
    current_admin: User = Depends(require_admin)
):
    user = await crud.update_user(user_id, {"is_active": True})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/admin/delete/{user_id}")
async def delete_user(
    user_id: str, 
    crud = Depends(get_user_crud), 
    current_admin: User = Depends(require_admin)
):
    success = await crud.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"detail": "User permanently deleted"}