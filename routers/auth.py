import httpx
from fastapi import Request, APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import os
from typing import Optional
import json
from database import get_database
from crud.user import UserCRUD
from models.user import User, RoleEnum, GenderEnum
from schemas.user import UserCreate
from utils.security import create_access_token
import secrets
import string

router = APIRouter(prefix="/auth", tags=["authentication"])

# Google OAuth Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "1035631189611-ou2ig6bn8d1uqkljcimbsogth9p67kh8.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")
GOOGLE_REDIRECT_URI = f"{BASE_URL}/auth/google/callback"

print(f"🔧 OAuth Configuration Loaded:")
print(f"   BASE_URL: {BASE_URL}")
print(f"   REDIRECT_URI: {GOOGLE_REDIRECT_URI}")
print(f"   CLIENT_ID: {GOOGLE_CLIENT_ID}")

class GoogleTokenRequest(BaseModel):
    code: str

class GoogleUserInfo(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None

def generate_random_password(length=16):
    """Generate a random password for Google OAuth users"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    if not any(c.isupper() for c in password):
        password += 'A'
    if not any(c.islower() for c in password):
        password += 'a'
    if not any(c.isdigit() for c in password):
        password += '1'
    return password

async def get_google_tokens(code: str):
    """Exchange authorization code for access token"""
    print(f"🔄 Exchanging code for tokens with Google...")
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_REDIRECT_URI,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        
        if response.status_code != 200:
            print(f"❌ Token exchange failed: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for tokens"
            )
        
        tokens = response.json()
        print(f"✅ Token exchange successful, access_token received: {bool(tokens.get('access_token'))}")
        return tokens

async def get_google_user_info(access_token: str):
    """Get user info from Google using access token"""
    print(f"🔄 Getting user info from Google...")
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(userinfo_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to get user info: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        user_data = response.json()
        print(f"✅ User info received: {user_data.get('email')} - {user_data.get('name')}")
        return GoogleUserInfo(**user_data)

@router.post("/google")
async def google_auth(request: GoogleTokenRequest, db=Depends(get_database)):
    """Handle Google OAuth callback - return token in response body"""
    try:
        print(f"🔍 Starting Google OAuth POST processing...")
        
        # Exchange code for tokens
        tokens = await get_google_tokens(request.code)
        access_token = tokens.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received from Google"
            )
        
        # Get user info from Google
        google_user = await get_google_user_info(access_token)
        
        crud = UserCRUD(db)
        
        # Check if user already exists
        existing_user = await crud.get_user_by_email(google_user.email)
        
        if existing_user:
            # User exists, log them in
            print(f"✅ Existing user found: {existing_user.email}")
            user = existing_user
        else:
            # Create new user with Google info
            print(f"🆕 Creating new user for: {google_user.email}")
            random_password = generate_random_password()
            
            # Create username from email (remove @domain.com)
            base_username = google_user.email.split('@')[0]
            username = base_username
            
            # Ensure username is unique
            counter = 1
            while await crud.get_user_by_username(username):
                username = f"{base_username}{counter}"
                counter += 1
            
            print(f"📝 Creating user with username: {username}")
            
            # Create UserCreate object
            user_data = UserCreate(
                full_name=google_user.name,
                username=username,
                email=google_user.email.lower(),
                password=random_password,
                role=RoleEnum.student,
                date_of_birth="2000-01-01",
                phone_number="",
                gender=GenderEnum.other,
                bio=f"Google OAuth user - {google_user.name}"
            )
            
            # Create user with avatar URL
            user = await crud.create_user(
                user_data=user_data,
                avatar_url=google_user.picture
            )
            
            if not user:
                print(f"❌ Failed to create user in database")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user from Google account"
                )
            print(f"✅ New user created successfully: {user.email}")
        
        # Update last login
        await crud.update_last_login(user.id)
        print(f"✅ Last login updated for user: {user.id}")
        
        # Create JWT token with 30-day expiration
        jwt_token = create_access_token(
            data={"sub": user.email, "role": user.role}
        )
        print(f"✅ JWT token created for user: {user.email}")

        # REMOVED: Cookie setting
        # set_auth_cookie(response, jwt_token)

        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "expires_in": 30 * 24 * 60 * 60,  # 30 days in seconds
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "username": user.username,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "is_active": user.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Google auth error: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.get("/google/url")
async def get_google_auth_url(request: Request):
    """Get Google OAuth URL for frontend with state parameter"""
    
    print(f"🔗 Using GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI}")
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=email profile&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    
    print(f"🔗 Generated Google auth URL: {auth_url}")
    return {"auth_url": auth_url}

@router.get("/google/callback")
async def google_callback(
    code: str = None, 
    error: str = None, 
    error_description: str = None,
    state: str = None,
    db=Depends(get_database)
):
    """Handle Google OAuth callback - return token in JavaScript"""
    print(f"🔍 Google callback received - code: {code is not None}, error: {error}, state: {state}")
    
    # Determine if this is signup or signin from state parameter
    is_signup = state == "signup"
    origin_page = "signin" if not is_signup else "signup"
    
    print(f"🎯 OAuth Flow Type: {'SIGNUP' if is_signup else 'SIGNIN'}")
    
    if error:
        error_msg = f"Google OAuth error: {error}"
        if error_description:
            error_msg += f" - {error_description}"
        print(f"❌ Google OAuth error: {error_msg}")
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Error</title>
            <script>
                localStorage.setItem('auth_error', '{error_msg}');
                window.location.href = '/{origin_page}.html';
            </script>
        </head>
        <body>
            <p>Redirecting...</p>
        </body>
        </html>
        """)
    
    if not code:
        print("❌ No authorization code received")
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Error</title>
            <script>
                localStorage.setItem('auth_error', 'No authorization code received');
                window.location.href = '/{origin_page}.html';
            </script>
        </head>
        <body>
            <p>Redirecting...</p>
        </body>
        </html>
        """)
    
    try:
        print("🔄 Exchanging code for tokens...")
        tokens = await get_google_tokens(code)
        access_token = tokens.get("access_token")
        
        if not access_token:
            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Error</title>
                <script>
                    localStorage.setItem('auth_error', 'No access token received from Google');
                    window.location.href = '/{origin_page}.html';
                </script>
            </head>
            <body>
                <p>Redirecting...</p>
            </body>
            </html>
            """)
        
        # Get user info from Google
        google_user = await get_google_user_info(access_token)
        print(f"🔍 Starting Google OAuth callback processing...")
        print(f"📧 Google user email: {google_user.email}")
        print(f"👤 Google user name: {google_user.name}")
        
        crud = UserCRUD(db)
        
        # Check if user already exists
        existing_user = await crud.get_user_by_email(google_user.email)
        user_was_created = False
        action_type = "signin"
        
        if existing_user:
            user = existing_user
            print(f"✅ Existing user found: {user.email}")
            if is_signup:
                print("ℹ️ Existing user attempting sign-up - treating as signin")
                action_type = "signin"
            else:
                action_type = "signin"
        else:
            # Create new user
            print(f"🆕 Creating new user for: {google_user.email}")
            random_password = generate_random_password()
            base_username = google_user.email.split('@')[0]
            username = base_username
            
            # Ensure username is unique
            counter = 1
            while await crud.get_user_by_username(username):
                username = f"{base_username}{counter}"
                counter += 1
            
            print(f"📝 Creating user with username: {username}")
            
            # Create UserCreate object
            user_data = UserCreate(
                full_name=google_user.name,
                username=username,
                email=google_user.email.lower(),
                password=random_password,
                role=RoleEnum.student,
                date_of_birth="2000-01-01",
                phone_number="",
                gender=GenderEnum.other,
                bio=f"Google OAuth user - {google_user.name}"
            )
            
            # Create user with avatar URL
            user = await crud.create_user(
                user_data=user_data,
                avatar_url=google_user.picture
            )
            
            if not user:
                print(f"❌ Failed to create user in database")
                return HTMLResponse(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Authentication Error</title>
                    <script>
                        localStorage.setItem('auth_error', 'Failed to create user account');
                        window.location.href = '/{origin_page}.html';
                    </script>
                </head>
                <body>
                    <p>Redirecting...</p>
                </body>
                </html>
                """)
            
            user_was_created = True
            action_type = "signup"
            print(f"✅ New user created successfully: {user.email}")
        
        # Update last login
        await crud.update_last_login(user.id)
        print(f"✅ Last login updated for user: {user.id}")
        
        # Create JWT token with 30-day expiration
        jwt_token = create_access_token(data={"sub": user.email, "role": user.role})
        print(f"✅ JWT token created for user: {user.email}")
        
        # Prepare user data
        user_data_dict = {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "username": user.username,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active
        }

        # Escape the JSON properly for JavaScript
        user_json = json.dumps(user_data_dict).replace("'", "\\'")
        
        # Custom messaging based on the actual action that occurred
        if action_type == "signup":
            success_title = "Account Created! 🎉"
            success_message = f"Welcome to Dakadēmia, {user.full_name}! Your account has been successfully created."
            toast_type = "success"
        else:
            success_title = "Welcome Back! 👋"
            success_message = f"Welcome back, {user.full_name}!"
            toast_type = "success"
        
        # UPDATED: Store token in localStorage instead of setting cookie
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <script>
                // Store user data and token in localStorage
                localStorage.setItem('user', '{user_json}');
                localStorage.setItem('access_token', '{jwt_token}');
                localStorage.setItem('token_type', 'bearer');
                localStorage.setItem('token_expires_in', '{30 * 24 * 60 * 60}'); // 30 days in seconds
                
                // Store custom success messaging
                localStorage.setItem('auth_success_title', '{success_title}');
                localStorage.setItem('auth_success_message', '{success_message}');
                localStorage.setItem('auth_success_type', '{toast_type}');
                localStorage.setItem('auth_action_type', '{action_type}');
                
                // Determine redirect URL based on user role
                const userRole = '{user.role}';
                let redirectUrl;
                
                if (userRole === 'admin') {{
                    redirectUrl = '/static/dashboards/Admin-Dashboard-Overview.html';
                }} else {{
                    redirectUrl = '/static/dashboards/Student-Dashboard-Overview.html';
                }}
                
                // Redirect to dashboard
                window.location.href = redirectUrl;
            </script>
        </head>
        <body>
            <p>Authentication successful! Redirecting...</p>
        </body>
        </html>
        """
        
        # REMOVED: Cookie setting
        response = HTMLResponse(html_content)
        
        return response
            
    except Exception as e:
        print(f"❌ Google callback error: {str(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        # Escape the error message for JavaScript
        error_message = str(e).replace("'", "\\'")
        
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Error</title>
            <script>
                localStorage.setItem('auth_error', 'Authentication failed: {error_message}');
                localStorage.setItem('auth_error_title', 'Authentication Failed');
                window.location.href = '/{origin_page}.html';
            </script>
        </head>
        <body>
            <p>Redirecting...</p>
        </body>
        </html>
        """)

@router.get("/google/setup")
async def google_setup_info():
    """Endpoint to check Google OAuth setup"""
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "has_secret": bool(GOOGLE_CLIENT_SECRET and GOOGLE_CLIENT_SECRET != "YOUR_CLIENT_SECRET_HERE"),
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "message": "Please set GOOGLE_CLIENT_SECRET in the code"
    }

@router.get("/google/test")
async def test_google_config():
    """Test Google OAuth configuration"""
    if GOOGLE_CLIENT_SECRET == "YOUR_CLIENT_SECRET_HERE":
        return {
            "status": "error",
            "message": "Client secret not configured. Please generate it in Google Cloud Console and update the code."
        }
    
    return {
        "status": "success", 
        "message": "Google OAuth is properly configured"
    }