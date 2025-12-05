from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os

from database import create_indexes, close_mongo_connection
from routers import courses, users, auth, lesson, assignment, quiz

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting LMS API with MongoDB Atlas...")
    await create_indexes()
    yield
    # Shutdown
    await close_mongo_connection()

# Define public endpoints that don't require authentication
PUBLIC_ENDPOINTS = [
    ("/", "GET"),
    ("/health", "GET"),
    ("/debug/cors-test", "GET"),
    ("/debug/auth", "GET"),
    ("/debug/routes", "GET"),
    ("/users/signup", "POST"),
    ("/users/login", "POST"),
    ("/users/logout", "POST"),
    ("/users/session", "GET"),
    ("/auth/google/url", "GET"),
    ("/auth/google/callback", "GET"),
    ("/auth/google/setup", "GET"),
    ("/auth/google/test", "GET"),
    ("/auth/google", "POST"),
    ("/docs", "GET"),
    ("/redoc", "GET"),
    ("/openapi.json", "GET"),
    ("/swagger-info", "GET"),
    ("/api/check-auth-status", "GET"),
]

app = FastAPI(
    title="Curra LMS API",
    description="""Curra Learning Management System Backend API

## Authentication

### Option 1: Login via Swagger UI
1. Click the **"Authorize"** button below  
2. Enter your **username** and **password**  
3. Click **"Authorize"**  
4. Swagger will automatically get a token and use it for all requests  

### Option 2: Manual Login
1. Use `/users/login` endpoint with username/password  
2. Copy the `access_token` from response  
3. Click "Authorize" and enter: `Bearer your_token_here`  

### Public Endpoints
These don't require authentication:
- `/users/signup` - Create new account  
- `/users/login` - Login to get token  
- `/health` - Health check  
- `/docs` - This documentation""",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "tagsSorter": "alpha",
        "displayOperationId": False,
        "defaultModelsExpandDepth": 1,
        "defaultModelExpandDepth": 1,
    }
)

# Enhanced CORS configuration
def get_allowed_origins():
    """Get allowed origins based on environment"""
    env_origins = os.getenv("ALLOWED_ORIGINS", "")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    
    # Default origins
    environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "production":
        return [
            "https://curralms.onrender.com",
            "https://curralms-frontend.onrender.com",
            "https://curralms-backend.onrender.com",
        ]
    else:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
    expose_headers=["*"]
)

# Serve static files (for avatars and frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routers WITHOUT /api prefix
app.include_router(courses.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(lesson.router)
app.include_router(assignment.router)
app.include_router(quiz.router)

# Root endpoint
@app.get("/")
async def read_root():
    return {
        "message": "Curra LMS API is running", 
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "login_info": "Use /users/login endpoint or click 'Authorize' in Swagger UI"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running smoothly"}

# Swagger info endpoint
@app.get("/swagger-info")
async def swagger_info():
    """Information about how to use Swagger authentication"""
    return {
        "message": "How to use Swagger authentication:",
        "steps": [
            "1. Go to /docs endpoint",
            "2. Click the 'Authorize' button in top-right corner",
            "3. Enter your username and password",
            "4. Click 'Authorize' to login",
            "5. Now all authenticated endpoints will include the token automatically"
        ],
        "auth_endpoints": {
            "login": "/users/login (POST) - Username/Password form",
            "signup": "/users/signup (POST)",
            "logout": "/users/logout (POST)"
        }
    }

# CORS Debug Endpoint
@app.get("/debug/cors-test")
async def cors_test(request: Request):
    """Test CORS and Authorization header functionality"""
    origin = request.headers.get("origin")
    auth_header = request.headers.get("authorization")
    
    return {
        "message": "CORS Test Endpoint - Authorization Headers",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "request_origin": origin,
        "authorization_header_received": auth_header is not None,
        "cors_configuration": {
            "allow_credentials": True,
            "allow_origins": get_allowed_origins(),
            "allow_headers": ["Authorization", "Content-Type"]
        }
    }

# Auth Debug Endpoint
@app.get("/debug/auth")
async def debug_auth(request: Request):
    """Debug authentication headers"""
    auth_header = request.headers.get("authorization")
    
    return {
        "authorization_header": auth_header,
        "headers_received": {
            "origin": request.headers.get("origin"),
            "authorization": auth_header,
            "content_type": request.headers.get("content-type")
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "message": "Check if Authorization header exists"
    }

# Debug Routes Endpoint - to check what routes are registered
@app.get("/debug/routes")
async def debug_routes():
    """Debug all registered routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": routes}

# Custom OpenAPI configuration with OAuth2 Password Flow
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    print("🔄 Generating custom OpenAPI schema with OAuth2 password flow...")
    
    openapi_schema = get_openapi(
        title="Curra LMS API",
        version="1.0.0",
        description="""Curra Learning Management System Backend API

## Authentication

### Option 1: Login via Swagger UI
1. Click the **"Authorize"** button below  
2. Enter your **username** and **password**  
3. Click **"Authorize"**  
4. Swagger will automatically get a token and use it for all requests  

### Option 2: Manual Login
1. Use `/users/login` endpoint with username/password  
2. Copy the `access_token` from response  
3. Click "Authorize" and enter: `Bearer your_token_here`  

### Public Endpoints
These don't require authentication:
- `/users/signup` - Create new account  
- `/users/login` - Login to get token  
- `/health` - Health check  
- `/docs` - This documentation""",
        routes=app.routes,
    )
    
    # Initialize components if not exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    # Add OAuth2 password flow for Swagger UI login form
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/users/login",
                    "scopes": {},
                    "description": "Enter your username and password to get a token"
                }
            },
            "description": "Enter username and password to login"
        },
        # Keep BearerAuth for manual token entry
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Manually enter JWT token: Bearer your_token"
        }
    }
    
    # Add security definitions for login endpoint specifically
    if "/users/login" in openapi_schema.get("paths", {}):
        login_path = openapi_schema["paths"]["/users/login"]
        if "post" in login_path:
            login_path["post"]["tags"] = ["auth"]
            login_path["post"]["summary"] = "Login with username/password"
            login_path["post"]["description"] = "Returns JWT token for authentication"
            
            # Add request body schema for login
            login_path["post"]["requestBody"] = {
                "required": True,
                "content": {
                    "application/x-www-form-urlencoded": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "username": {
                                    "type": "string",
                                    "example": "user@example.com"
                                },
                                "password": {
                                    "type": "string",
                                    "example": "password123"
                                }
                            },
                            "required": ["username", "password"]
                        }
                    },
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "username": {
                                    "type": "string",
                                    "example": "user@example.com"
                                },
                                "password": {
                                    "type": "string",
                                    "example": "password123"
                                }
                            },
                            "required": ["username", "password"]
                        }
                    }
                }
            }
    
    # Apply security to all endpoints except public ones
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            # Skip if it's the login endpoint itself
            if path == "/users/login" and method == "post":
                continue
                
            # Check if this endpoint is in public endpoints
            if (path, method.upper()) in PUBLIC_ENDPOINTS:
                # Remove security if present
                if "security" in operation:
                    del operation["security"]
            else:
                # Add OAuth2 security requirement (for password flow)
                operation["security"] = [{"OAuth2PasswordBearer": []}]
    
    app.openapi_schema = openapi_schema
    print("✅ OpenAPI schema generated with OAuth2 password flow")
    return app.openapi_schema

# Apply the custom OpenAPI schema
app.openapi = custom_openapi

# Optional: Add endpoint to check if security is working
@app.get("/api/check-auth-status")
async def check_auth_status(request: Request):
    """Check if authentication is working in Swagger"""
    auth_header = request.headers.get("authorization")
    
    return {
        "authentication_header_received": bool(auth_header),
        "header_value": auth_header,
        "message": "If you see 'Bearer ...' above, Swagger authentication is working!",
        "swagger_login_instructions": "Go to /docs and click 'Authorize' button, enter username/password"
    }

# Alternative OpenAPI endpoint with debugging
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    """Direct endpoint to see OpenAPI schema (for debugging)"""
    schema = custom_openapi()
    return JSONResponse(content=schema)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )