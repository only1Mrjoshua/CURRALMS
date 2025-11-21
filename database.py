# database.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
import os
from typing import Optional
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "lms_db")

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    is_connected: bool = False

mongodb = MongoDB()

async def get_database():
    if mongodb.client is None:
        print(f"🔗 Connecting to MongoDB Atlas...")
        
        try:
            mongodb.client = AsyncIOMotorClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                maxPoolSize=10,
                retryWrites=True
            )
            
            # Test connection
            await mongodb.client.admin.command('ping')
            mongodb.is_connected = True
            print("✅ Successfully connected to MongoDB Atlas!")
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            mongodb.is_connected = False
            # Still create the client for fallback operations
            mongodb.client = AsyncIOMotorClient(MONGODB_URL)
    
    return mongodb.client[DATABASE_NAME]

async def close_mongo_connection():
    if mongodb.client:
        mongodb.client.close()
        print("🔌 MongoDB connection closed")

async def create_indexes():
    try:
        db = await get_database()
        
        # Test if we're actually connected
        try:
            await db.command('ping')
            print("📊 Creating database indexes...")
            
            # User indexes
            await db.users.create_index([("email", ASCENDING)], unique=True)
            await db.users.create_index([("username", ASCENDING)], unique=True)
            await db.users.create_index([("role", ASCENDING)])
            await db.users.create_index([("is_active", ASCENDING)])
            await db.users.create_index([("created_at", ASCENDING)])
            await db.users.create_index([("last_login", ASCENDING)])
            print("✅ User indexes created successfully")
            
            # Course indexes
            await db.courses.create_index([("title", ASCENDING)])
            await db.courses.create_index([("category", ASCENDING)])
            await db.courses.create_index([("instructor_id", ASCENDING)])
            await db.courses.create_index([("is_active", ASCENDING), ("is_public", ASCENDING)])
            print("✅ Course indexes created successfully")
            
            # Module indexes
            await db.modules.create_index([("course_id", ASCENDING)])
            print("✅ Module indexes created successfully")
            
            # Lesson indexes
            await db.lessons.create_index([("module_id", ASCENDING)])
            print("✅ Lesson indexes created successfully")
            
            # Enrollment indexes
            await db.enrollments.create_index([("user_id", ASCENDING)])
            await db.enrollments.create_index([("course_id", ASCENDING)])
            await db.enrollments.create_index([("user_id", ASCENDING), ("course_id", ASCENDING)], unique=True)
            print("✅ Enrollment indexes created successfully")
            
            # Quiz indexes
            await db.quizzes.create_index([("lesson_id", ASCENDING)])
            await db.quizzes.create_index([("course_id", ASCENDING)])
            print("✅ Quiz indexes created successfully")
            
            print("🎉 All database indexes created successfully!")
            
        except Exception as e:
            print(f"⚠️  Could not create indexes - no active connection: {e}")
            
    except Exception as e:
        print(f"⚠️  Error in index creation: {e}")