from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from database import create_indexes, close_mongo_connection
from routers import courses, users, auth, lesson, assignment, quiz
from dependencies import oauth2_scheme

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting LMS API with MongoDB Atlas...")
    await create_indexes()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI()

# Include routers
app.include_router(courses.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(lesson.router)
app.include_router(assignment.router)
app.include_router(quiz.router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for avatars)
app.mount("/static", StaticFiles(directory="static"), name="static")

# In main.py - replace your custom_openapi function with this:
# Serve the main HTML files
@app.get("/")
async def read_index():
    return FileResponse("static/signin.html")

@app.get("/signin.html")
async def read_signin():
    return FileResponse("static/signin.html")

@app.get("/signup.html")
async def read_signup():
    return FileResponse("static/signup.html")

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

