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

# Enhanced CORS configuration - UPDATED FOR AUTHORIZATION HEADERS
def get_allowed_origins():
    """Get allowed origins based on environment"""
    env_origins = os.getenv("ALLOWED_ORIGINS", "")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    
    # Default origins - UPDATED FOR RENDER
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

# CORS middleware - UPDATED FOR AUTHORIZATION HEADERS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,  # Keep this True for other cookies if needed
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],  # Ensure Authorization header is allowed
    expose_headers=["*"]
)

# Include routers
app.include_router(courses.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(lesson.router)
app.include_router(assignment.router)
app.include_router(quiz.router)

# Serve static files (for avatars)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    return {"message": "Curra LMS API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running smoothly"}

# UPDATED CORS Debug Endpoint - Removed cookie testing
@app.get("/debug/cors-test")
async def cors_test(request: Request):
    """Test CORS and Authorization header functionality"""
    origin = request.headers.get("origin")
    auth_header = request.headers.get("authorization")
    
    # Get environment
    environment = os.getenv("ENVIRONMENT", "development")
    
    return {
        "message": "CORS Test Endpoint - Authorization Headers",
        "environment": environment,
        "request_origin": origin,
        "authorization_header_received": auth_header is not None,
        "cors_configuration": {
            "allow_credentials": True,
            "allow_origins": get_allowed_origins(),
            "allow_headers": ["Authorization", "Content-Type"]
        }
    }

# UPDATED Auth Debug Endpoint
@app.get("/debug/auth")
async def debug_auth(request: Request):
    """Debug authentication headers"""
    auth_header = request.headers.get("authorization")
    headers = dict(request.headers)
    
    return {
        "authorization_header": auth_header,
        "headers_received": {
            "origin": headers.get("origin"),
            "authorization": auth_header,
            "content_type": headers.get("content-type")
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "message": "Check if Authorization header exists"
    }

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve frontend files for SPA routing in production
    """
    # List of API route prefixes that should NOT be handled by this route
    api_routes = [
        "students/", "users/", "courses/", "lessons/", 
        "assignments/", "quizzes/", "auth/", "debug/"
    ]
    
    # If it's an API route, return 404
    if any(full_path.startswith(api_route) for api_route in api_routes):
        return {"error": "API endpoint not found"}
    
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
    
    # Return 404 for other routes that don't exist
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
        ("/debug/cors-test", "GET"),
        ("/debug/auth", "GET"),
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