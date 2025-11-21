from typing import List, Optional
from bson import ObjectId
from pymongo import ReturnDocument
from datetime import datetime
import re

from models.course import Course, CourseModule, Lesson, Quiz, Enrollment
from schemas.course import (
    CourseCreate, CourseUpdate, 
    CourseModuleCreate, LessonCreate,
    QuizCreate, EnrollmentCreate, EnrollmentUpdate
)

class CourseCRUD:
    def __init__(self):
        # Don't pass db in constructor, get it when needed
        self.db = None

    async def _get_db(self):
        """Get database connection when needed"""
        if self.db is None:
            from database import get_database
            self.db = await get_database()
        return self.db

    async def _is_connected(self):
        """Check if we have a working database connection"""
        try:
            db = await self._get_db()
            await db.command('ping')
            return True
        except:
            return False

    def _convert_objectids_to_strings(self, data: dict) -> dict:
        """Convert all ObjectId fields to strings in the data"""
        if not data:
            return data
            
        converted = data.copy()
        
        # Convert _id to string
        if '_id' in converted and converted['_id']:
            converted['_id'] = str(converted['_id'])
        
        # Convert instructor_id to string
        if 'instructor_id' in converted and converted['instructor_id']:
            converted['instructor_id'] = str(converted['instructor_id'])
        
        # Convert other potential ObjectId fields
        for key in ['course_id', 'module_id', 'lesson_id', 'user_id', 'current_lesson_id', 'next_course_id']:
            if key in converted and converted[key] and isinstance(converted[key], ObjectId):
                converted[key] = str(converted[key])
        
        # Handle completed_lessons array
        if 'completed_lessons' in converted and converted['completed_lessons']:
            converted['completed_lessons'] = [str(lesson_id) for lesson_id in converted['completed_lessons']]
        
        return converted

    # Course operations - RETURN PLAIN DICTS INSTEAD OF COURSE OBJECTS
    async def get_course(self, course_id: str) -> Optional[dict]:
        if not await self._is_connected():
            print("⚠️  No database connection")
            return None
            
        try:
            db = await self._get_db()
            course_data = await db.courses.find_one({"_id": ObjectId(course_id)})
            if course_data:
                # Convert all ObjectIds to strings and return as plain dict
                return self._convert_objectids_to_strings(course_data)
            return None
        except Exception as e:
            print(f"Error getting course: {e}")
            return None

    async def get_courses(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        category: Optional[str] = None,
        instructor_id: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[dict]:
        if not await self._is_connected():
            print("⚠️  No database connection")
            return []
            
        try:
            db = await self._get_db()
            query = {}  # Start with empty query
            
            # Only add is_active filter if explicitly requested
            if is_active is not None:
                query["is_active"] = is_active
                
            if category:
                # Use case-insensitive matching for category in general get_courses too
                query["category"] = {"$regex": f"^{re.escape(category)}$", "$options": "i"}
            if instructor_id:
                query["instructor_id"] = ObjectId(instructor_id)
            
            cursor = db.courses.find(query).skip(skip).limit(limit)
            courses_data = await cursor.to_list(length=limit)
            
            # Convert all ObjectIds to strings and return plain dicts
            serializable_courses = []
            for course_data in courses_data:
                clean_course = self._convert_objectids_to_strings(course_data)
                serializable_courses.append(clean_course)
            
            return serializable_courses
        except Exception as e:
            print(f"Error getting courses: {e}")
            return []

    async def create_course(self, course: CourseCreate) -> Optional[dict]:
        if not await self._is_connected():
            print("⚠️  No database connection")
            return None
            
        try:
            db = await self._get_db()
            # Convert CourseCreate to dict, excluding unset values
            course_dict = course.model_dump(exclude_unset=True)
            
            # Handle instructor_id conversion
            if course.instructor_id:
                course_dict["instructor_id"] = ObjectId(course.instructor_id)
            
            # Set timestamps
            course_dict["created_at"] = datetime.utcnow()
            course_dict["updated_at"] = datetime.utcnow()
            
            result = await db.courses.insert_one(course_dict)
            created_course = await db.courses.find_one({"_id": result.inserted_id})
            
            if created_course:
                # Convert all ObjectIds to strings for response
                return self._convert_objectids_to_strings(created_course)
            return None
        except Exception as e:
            print(f"Error creating course: {e}")
            return None

    async def update_course(self, course_id: str, course_update: CourseUpdate) -> Optional[dict]:
        if not await self._is_connected():
            print("⚠️  No database connection")
            return None
            
        try:
            db = await self._get_db()
            update_data = {k: v for k, v in course_update.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = datetime.utcnow()
            
            result = await db.courses.find_one_and_update(
                {"_id": ObjectId(course_id)},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            
            if result:
                # Convert all ObjectIds to strings
                return self._convert_objectids_to_strings(result)
            return None
        except Exception as e:
            print(f"Error updating course: {e}")
            return None

    async def delete_course(self, course_id: str) -> bool:
        if not await self._is_connected():
            print("⚠️  No database connection")
            return False
            
        try:
            db = await self._get_db()
            result = await db.courses.delete_one({"_id": ObjectId(course_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting course: {e}")
            return False

    # Enrollment operations - RETURN PLAIN DICTS
    async def create_enrollment(self, enrollment: EnrollmentCreate) -> Optional[dict]:
        if not await self._is_connected():
            print("⚠️  No database connection")
            return None
            
        try:
            db = await self._get_db()
            # Check if enrollment already exists
            existing = await db.enrollments.find_one({
                "user_id": ObjectId(enrollment.user_id),
                "course_id": ObjectId(enrollment.course_id)
            })
            if existing:
                return self._convert_objectids_to_strings(existing)
            
            # Create enrollment with ALL required fields
            enrollment_dict = {
                "user_id": ObjectId(enrollment.user_id),
                "course_id": ObjectId(enrollment.course_id),
                "enrolled_at": datetime.utcnow(),
                "progress_percentage": 0.0,
                "current_lesson_id": None,
                "status": "enrolled",
                "completed_lessons": [],
                "completed_at": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await db.enrollments.insert_one(enrollment_dict)
            created_enrollment = await db.enrollments.find_one({"_id": result.inserted_id})
            
            if created_enrollment:
                return self._convert_objectids_to_strings(created_enrollment)
            return None
        except Exception as e:
            print(f"Error creating enrollment: {e}")
            return None

    async def update_enrollment(self, enrollment_id: str, enrollment_update: EnrollmentUpdate) -> Optional[dict]:
        if not await self._is_connected():
            print("⚠️  No database connection")
            return None
            
        try:
            db = await self._get_db()
            update_data = {k: v for k, v in enrollment_update.model_dump(exclude_unset=True).items() if v is not None}
            update_data["updated_at"] = datetime.utcnow()  # Add updated_at
            
            result = await db.enrollments.find_one_and_update(
                {"_id": ObjectId(enrollment_id)},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            
            if result:
                return self._convert_objectids_to_strings(result)
            return None
        except Exception as e:
            print(f"Error updating enrollment: {e}")
            return None

    async def get_user_enrollments(self, user_id: str) -> List[dict]:
        if not await self._is_connected():
            return []
            
        try:
            db = await self._get_db()
            cursor = db.enrollments.find({"user_id": ObjectId(user_id)})
            enrollments_data = await cursor.to_list(length=100)
            
            enrollments = []
            for enrollment_data in enrollments_data:
                clean_enrollment = self._convert_objectids_to_strings(enrollment_data)
                enrollments.append(clean_enrollment)
            
            return enrollments
        except Exception as e:
            print(f"Error getting user enrollments: {e}")
            return []

    async def get_course_enrollments(self, course_id: str) -> List[dict]:
        if not await self._is_connected():
            return []
            
        try:
            db = await self._get_db()
            cursor = db.enrollments.find({"course_id": ObjectId(course_id)})
            enrollments_data = await cursor.to_list(length=100)
            
            enrollments = []
            for enrollment_data in enrollments_data:
                clean_enrollment = self._convert_objectids_to_strings(enrollment_data)
                enrollments.append(clean_enrollment)
            
            return enrollments
        except Exception as e:
            print(f"Error getting course enrollments: {e}")
            return []
    
    # Additional course query methods - RETURN PLAIN DICTS
    async def get_courses_by_level_and_category(self, level: str, category: str) -> List[dict]:
        """Get courses by level and category"""
        if not await self._is_connected():
            return []
            
        try:
            db = await self._get_db()
            query = {
                "level": level,
                "category": {"$regex": f"^{re.escape(category)}$", "$options": "i"},
                "$or": [
                    {"is_active": True},
                    {"is_active": {"$exists": False}}
                ]
            }
            cursor = db.courses.find(query)
            courses_data = await cursor.to_list(length=100)
            
            courses = []
            for course_data in courses_data:
                clean_course = self._convert_objectids_to_strings(course_data)
                courses.append(clean_course)
            
            return courses
        except Exception as e:
            print(f"Error getting courses by level and category: {e}")
            return []

    async def get_active_courses(self) -> List[dict]:
        """Get all active courses"""
        if not await self._is_connected():
            return []
            
        try:
            db = await self._get_db()
            query = {
                "$or": [
                    {"is_active": True},
                    {"is_active": {"$exists": False}}
                ]
            }
            cursor = db.courses.find(query)
            courses_data = await cursor.to_list(length=100)
            
            courses = []
            for course_data in courses_data:
                clean_course = self._convert_objectids_to_strings(course_data)
                courses.append(clean_course)
            
            return courses
        except Exception as e:
            print(f"Error getting active courses: {e}")
            return []

    async def get_course_by_level(self, level: str) -> List[dict]:
        """Get courses by level"""
        if not await self._is_connected():
            return []
            
        try:
            db = await self._get_db()
            query = {
                "level": level,
                "$or": [
                    {"is_active": True},
                    {"is_active": {"$exists": False}}
                ]
            }
            cursor = db.courses.find(query)
            courses_data = await cursor.to_list(length=100)
            
            courses = []
            for course_data in courses_data:
                clean_course = self._convert_objectids_to_strings(course_data)
                courses.append(clean_course)
            
            return courses
        except Exception as e:
            print(f"Error getting courses by level: {e}")
            return []

    async def get_courses_by_category(self, category: str, is_active: bool = True) -> List[dict]:
        """Get courses by category - FIXED WITH CASE-INSENSITIVE MATCHING"""
        print(f"🔍 CRUD DEBUG: Looking for category '{category}'")
        
        if not await self._is_connected():
            print("⚠️  No database connection")
            return []
            
        try:
            db = await self._get_db()
            # Use case-insensitive regex matching for category
            query = {
                "category": {"$regex": f"^{re.escape(category)}$", "$options": "i"},
                "$or": [
                    {"is_active": True},
                    {"is_active": {"$exists": False}}
                ]
            }
            
            print(f"🔍 CRUD DEBUG: Case-insensitive query: {query}")
            
            cursor = db.courses.find(query)
            courses_data = await cursor.to_list(length=100)
            
            print(f"🔍 CRUD DEBUG: Found {len(courses_data)} courses with category pattern '{category}'")
            
            # If no results with exact pattern, try partial matching as fallback
            if len(courses_data) == 0:
                print(f"🔍 CRUD DEBUG: Trying partial matching...")
                partial_query = {
                    "category": {"$regex": category, "$options": "i"},
                    "$or": [
                        {"is_active": True},
                        {"is_active": {"$exists": False}}
                    ]
                }
                cursor = db.courses.find(partial_query)
                courses_data = await cursor.to_list(length=100)
                print(f"🔍 CRUD DEBUG: Partial match found {len(courses_data)} courses")
            
            # Debug: print what we found
            for i, course_data in enumerate(courses_data):
                print(f"🔍 CRUD DEBUG: Course {i+1}: {course_data.get('title', 'No title')} | "
                      f"Category: {course_data.get('category', 'No category')} | "
                      f"is_active: {course_data.get('is_active', 'Not set')}")
            
            # Convert all ObjectIds to strings and return plain dicts
            serializable_courses = []
            for course_data in courses_data:
                clean_course = self._convert_objectids_to_strings(course_data)
                serializable_courses.append(clean_course)
            
            print(f"🔍 CRUD DEBUG: Returning {len(serializable_courses)} courses as plain dicts")
            return serializable_courses
            
        except Exception as e:
            print(f"❌ CRUD DEBUG: Error getting courses by category: {e}")
            return []