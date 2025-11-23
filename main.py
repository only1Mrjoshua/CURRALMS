from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from database import create_indexes, close_mongo_connection
from routers import courses, users, auth, lesson, assignment, quiz
from dependencies import oauth2_scheme
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting LMS API with MongoDB Atlas...")
    await create_indexes()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(courses.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(lesson.router)
app.include_router(assignment.router)
app.include_router(quiz.router)

# CORS middleware - UPDATED FOR COOKIE AUTHENTICATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://curralms.onrender.com",
        "https://curralms-frontend.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:63342",
        "http://127.0.0.1:63342",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "null"  # For file protocol
    ],
    allow_credentials=True,  # CRITICAL FOR COOKIES
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # IMPORTANT FOR COOKIES
)

# Serve static files (for avatars)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return {"message": "Curra LMS API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running smoothly"}

# CORS Debug Endpoint - ADD THIS
@app.get("/debug/cors-test")
async def cors_test(request: Request, response: Response):
    """Test CORS and cookie functionality"""
    origin = request.headers.get("origin")
    cookies = request.cookies
    headers = dict(request.headers)
    
    # Set test cookies
    response.set_cookie(
        key="test_cookie",
        value="cors_works",
        httponly=False,  # Make accessible to JS for testing
        secure=False,
        samesite="lax",
        path="/"
    )
    
    response.set_cookie(
        key="http_only_test",
        value="http_only_works", 
        httponly=True,
        secure=False,
        samesite="lax",
        path="/"
    )
    
    return {
        "message": "CORS Test Endpoint",
        "request_origin": origin,
        "cookies_received": cookies,
        "headers": {
            "origin": headers.get("origin"),
            "cookie": headers.get("cookie"),
            "authorization": headers.get("authorization")
        },
        "cors_configuration": {
            "allow_credentials": True,
            "allow_origins": "See CORS middleware",
            "expose_headers": True
        }
    }

# Cookie Debug Endpoint
@app.get("/debug/cookies")
async def debug_cookies(request: Request):
    """Debug endpoint to check if cookies are being sent"""
    cookies = request.cookies
    headers = dict(request.headers)
    
    return {
        "cookies_received": cookies,
        "headers_received": {
            "origin": headers.get("origin"),
            "cookie": headers.get("cookie"),
            "authorization": headers.get("authorization")
        },
        "message": "Check if access_token cookie exists in 'cookies_received'"
    }

# Serve frontend files for production
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve frontend files for SPA routing in production
    """
    frontend_paths = [
        "", "signin.html", "signup.html", "index.html",
        "dashboards/", "courses/", "profile/"
    ]
    
    # Check if this is a frontend route
    if any(full_path.startswith(path) for path in frontend_paths) or '.' not in full_path:
        try:
            # Try to serve static files first
            return FileResponse(f"static/{full_path}" if full_path else "static/index.html")
        except:
            # Fallback to index.html for SPA routing
            return FileResponse("static/index.html")
    
    # Return 404 for API routes that don't exist
    return {"error": "Endpoint not found"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title="Curra LMS",
        version="1.0.0",
        description="Curra Learning Management System API Documentation",
        routes=app.routes,
    )
    
    # Add OAuth2 security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "users/login",
                    "scopes": {}
                }
            }
        }
    }
    
    # Apply security to all endpoints that have authentication dependencies
    for path, methods in openapi_schema["paths"].items():
        for method, details in methods.items():
            # Check if this endpoint requires authentication
            if endpoint_requires_auth(path, method.upper()):
                if "security" not in details:
                    details["security"] = [{"OAuth2PasswordBearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def endpoint_requires_auth(path: str, method: str) -> bool:
    """Check if an endpoint requires authentication"""
    # List of public endpoints that don't require auth
    public_endpoints = [
        ("/", "GET"),
        ("/health", "GET"),
        ("/users/signup", "POST"),
        ("/users/login", "POST"),
        ("/users/logout", "POST"),
        ("/users/session", "GET"),
        ("/auth/google/url", "GET"),
        ("/auth/google/callback", "GET"),
        ("/auth/google/setup", "GET"),
        ("/auth/google/test", "GET"),
        ("/auth/google", "POST"),
    ]
    
    if (path, method) in public_endpoints:
        return False
    
    # Check if the route has security dependencies
    for route in app.routes:
        if hasattr(route, 'path') and route.path == path:
            if hasattr(route, 'methods') and method in route.methods:
                # If route has dependencies, it likely requires auth
                if hasattr(route, 'dependencies') and route.dependencies:
                    return True
                # Check endpoint function dependencies
                if hasattr(route, 'endpoint') and hasattr(route.endpoint, 'dependencies'):
                    if route.endpoint.dependencies:
                        return True
    return True  # Default to requiring auth for security

app.openapi = custom_openapi

# Add CORS debug endpoint
@app.get("/debug/cors")
async def debug_cors_info(request: Request):
    """
    Debug endpoint to check CORS configuration
    """
    return {
        "allowed_origins": [
            "https://curralms.onrender.com",
            "https://curralms-frontend.onrender.com",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:8000",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ],
        "request_origin": request.headers.get("origin"),
        "allow_credentials": True,
        "cors_enabled": True
    }

@app.get("/debug/cookies")
async def debug_cookies(request: Request):
    """Debug endpoint to check if cookies are being sent"""
    cookies = request.cookies
    headers = dict(request.headers)
    
    return {
        "cookies_received": cookies,
        "headers_received": {
            "origin": headers.get("origin"),
            "cookie": headers.get("cookie"),
            "authorization": headers.get("authorization")
        },
        "message": "Check if access_token cookie exists in 'cookies_received'"
    }