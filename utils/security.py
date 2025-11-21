# utils/security.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt  # Use bcrypt directly instead of passlib

# Secret key for JWT - change this in production!
SECRET_KEY = "fhu5a0PfLz0zCKHk4Xg14Lk9jKMG2E5bTnh6aZp3NfE6d6shbw2"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

def hash_password(password: str) -> str:
    """Hash a password using bcrypt with length handling"""
    # Convert to bytes and truncate if too long
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Hash using bcrypt directly
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt with length handling"""
    try:
        # Convert to bytes and truncate if too long
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Convert stored hash to bytes
        hash_bytes = hashed_password.encode('utf-8')
        
        # Verify using bcrypt directly
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        print(f"❌ Password verification error: {e}")
        return False

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None