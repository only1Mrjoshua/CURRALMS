from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from database import create_indexes, close_mongo_connection
from routers import courses, users, auth, lesson, assignment, quiz
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting LMS API with MongoDB Atlas...")
    await create_indexes()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title="Curra LMS API",
    description="Curra Learning Management System Backend API",
    version="1.0.0",
    lifespan=lifespan
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
        "health": "/health"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running smoothly"}

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

# FIXED: Catch-all route for frontend SPA - PROPERLY excludes API routes
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """
    Serve frontend files for SPA routing in production
    This route ONLY handles frontend routes, NOT API routes
    """
    # List of API routes that should NEVER be handled by this route
    api_routes = [
        "courses", "users", "auth", "lessons", "assignments", "quizzes",
        "docs", "redoc", "openapi.json", "debug", "health"
    ]
    
    # Split the path to get the first segment
    first_segment = full_path.split('/')[0] if full_path else ""
    
    # If it's an API route or docs, let FastAPI handle it or return 404
    if first_segment in api_routes:
        # Let FastAPI handle the API route - if no route matches, it will return 404
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Frontend routes that should be served
    frontend_paths = [
        "", "signin", "signup", "dashboard", "courses", 
        "profile", "admin", "student", "dashboards"
    ]
    
    # Check if this is a frontend route
    is_frontend_route = (
        first_segment in frontend_paths or 
        '.' not in full_path or
        full_path in ['', 'index.html', 'signin.html', 'signup.html'] or
        any(full_path.startswith(path) for path in frontend_paths if path)
    )
    
    if is_frontend_route:
        try:
            # Try to serve the specific file
            if full_path and '.' in full_path and not full_path.endswith('/'):
                return FileResponse(f"static/{full_path}")
            else:
                # For SPA routes, serve index.html
                return FileResponse("static/index.html")
        except Exception as e:
            print(f"Frontend serving error: {e}")
            # Fallback to index.html
            return FileResponse("static/index.html")
    
    # If not a recognized frontend route and not an API route, return 404
    raise HTTPException(status_code=404, detail="Endpoint not found")

# Custom OpenAPI configuration
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
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Apply security to endpoints that require authentication
    for path, methods in openapi_schema["paths"].items():
        for method, details in methods.items():
            if endpoint_requires_auth(path, method.upper()):
                if "security" not in details:
                    details["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def endpoint_requires_auth(path: str, method: str) -> bool:
    """Check if an endpoint requires authentication"""
    # List of public endpoints that don't require auth
    public_endpoints = [
        ("/", "GET"),
        ("/health", "GET"),
        ("/debug/cors-test", "GET"),
        ("/debug/auth", "GET"),
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
    return False  # Default to not requiring auth for better UX

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )