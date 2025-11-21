from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from models.lesson import LessonCreate, LessonUpdate, LessonStatus

class LessonCRUD:
    def __init__(self, db):
        self.collection = db.lessons
        self.completions_collection = db.user_lesson_completions
    
    async def create_lesson(self, lesson: LessonCreate, created_by: str) -> dict:
        lesson_data = lesson.dict()
        
        # Convert date and time to strings for MongoDB storage
        if 'start_date' in lesson_data and lesson_data['start_date']:
            lesson_data['start_date'] = lesson_data['start_date'].isoformat()
        
        if 'start_time' in lesson_data and lesson_data['start_time']:
            lesson_data['start_time'] = lesson_data['start_time'].isoformat()
        
        # Convert enum values to strings
        if 'location_type' in lesson_data:
            lesson_data['location_type'] = lesson_data['location_type'].value
        
        if 'status' in lesson_data:
            lesson_data['status'] = lesson_data['status'].value
        
        # Clear unused location fields based on location_type
        if lesson_data.get('location_type') == 'zoom':
            lesson_data['google_meet_link'] = None
            lesson_data['classroom_location'] = None
        elif lesson_data.get('location_type') == 'google_meet':
            lesson_data['zoom_link'] = None
            lesson_data['classroom_location'] = None
        elif lesson_data.get('location_type') == 'physical_classroom':
            lesson_data['zoom_link'] = None
            lesson_data['google_meet_link'] = None
        
        lesson_data.update({
            "created_by": created_by,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        result = await self.collection.insert_one(lesson_data)
        created_lesson = await self.get_lesson_by_id(str(result.inserted_id))
        
        # Ensure the response is properly formatted
        if created_lesson and '_id' in created_lesson:
            created_lesson['_id'] = str(created_lesson['_id'])
            
        return created_lesson
    
    async def get_lesson_by_id(self, lesson_id: str) -> Optional[dict]:
        if not ObjectId.is_valid(lesson_id):
            return None
        lesson = await self.collection.find_one({"_id": ObjectId(lesson_id)})
        if lesson and '_id' in lesson:
            lesson['_id'] = str(lesson['_id'])
        return lesson
    
    async def get_lessons_by_course(self, course_id: str, include_inactive: bool = False) -> List[dict]:
        query = {"course_id": course_id}
        
        if not include_inactive:
            query["is_active"] = True
            
        cursor = self.collection.find(query).sort("start_date", 1).sort("start_time", 1)
        lessons = await cursor.to_list(length=None)
        
        # Convert ObjectId to string for all lessons
        for lesson in lessons:
            if '_id' in lesson:
                lesson["_id"] = str(lesson["_id"])
        
        return lessons
    
    async def get_lessons_by_category(self, category: str, include_inactive: bool = False) -> List[dict]:
        """Get lessons by category - FIXED VERSION"""
        print(f"🔍 CRUD DEBUG: Searching for lessons in category: '{category}'")
        
        # First, let's check what categories actually exist in the database
        all_categories = await self.collection.distinct("category")
        print(f"🔍 CRUD DEBUG: Available categories in DB: {all_categories}")
        
        # Build query - search by category field directly
        query = {"category": {"$regex": f"^{category}$", "$options": "i"}}  # Case-insensitive exact match
        
        if not include_inactive:
            query["is_active"] = True
            
        print(f"🔍 CRUD DEBUG: Final query: {query}")
        
        cursor = self.collection.find(query).sort("start_date", 1).sort("start_time", 1)
        lessons = await cursor.to_list(length=None)
        
        print(f"🔍 CRUD DEBUG: Found {len(lessons)} lessons in category '{category}'")
        
        for lesson in lessons:
            if '_id' in lesson:
                lesson["_id"] = str(lesson["_id"])
            print(f"🔍 CRUD DEBUG: Lesson - {lesson.get('title')}, Category: {lesson.get('category')}")
        
        return lessons
    
    async def get_upcoming_lessons(self, limit: int = 10) -> List[dict]:
        """Get upcoming lessons sorted by date and time"""
        query = {
            "status": {"$in": ["upcoming", "ongoing"]}
        }
        
        cursor = self.collection.find(query).sort("start_date", 1).sort("start_time", 1).limit(limit)
        lessons = await cursor.to_list(length=None)
        
        for lesson in lessons:
            if '_id' in lesson:
                lesson["_id"] = str(lesson["_id"])
        
        return lessons
    
    async def get_all_lessons_simple(self) -> List[dict]:
        """Get ALL lessons without any filtering - SIMPLE VERSION"""
        print("🔍 CRUD DEBUG: get_all_lessons_simple called - fetching ALL lessons")
        
        cursor = self.collection.find({}).sort("start_date", 1).sort("start_time", 1)
        lessons = await cursor.to_list(length=None)
        
        print(f"🔍 CRUD DEBUG: Retrieved {len(lessons)} total lessons")
        
        # Convert ObjectId to string for all lessons
        for lesson in lessons:
            if '_id' in lesson:
                lesson["_id"] = str(lesson["_id"])
        
        return lessons
    
    async def get_all_lessons(
        self,
        course_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[LessonStatus] = None
    ) -> List[dict]:
        """Get all lessons with optional filtering"""
        print("🔍 CRUD DEBUG: get_all_lessons called")
        
        query = {}
        
        if course_id:
            query["course_id"] = course_id
            print(f"🔍 CRUD DEBUG: Filtering by course_id: {course_id}")
            
        if category:
            query["category"] = category
            print(f"🔍 CRUD DEBUG: Filtering by category: {category}")
            
        if status:
            query["status"] = status.value
            print(f"🔍 CRUD DEBUG: Filtering by status: {status.value}")
        
        print(f"🔍 CRUD DEBUG: Final query: {query}")
        
        cursor = self.collection.find(query).sort("start_date", 1).sort("start_time", 1)
        lessons = await cursor.to_list(length=None)
        
        print(f"🔍 CRUD DEBUG: Retrieved {len(lessons)} lessons")
        
        # Convert ObjectId to string for all lessons
        for lesson in lessons:
            if '_id' in lesson:
                lesson["_id"] = str(lesson["_id"])
        
        return lessons
    
    async def update_lesson(self, lesson_id: str, update_data: LessonUpdate) -> Optional[dict]:
        if not ObjectId.is_valid(lesson_id):
            return None
        
        update_dict = {k: v for k, v in update_data.dict(exclude_unset=True).items() if v is not None}
        
        # Convert date and time to strings if present
        if 'start_date' in update_dict and update_dict['start_date']:
            update_dict['start_date'] = update_dict['start_date'].isoformat()
        
        if 'start_time' in update_dict and update_dict['start_time']:
            update_dict['start_time'] = update_dict['start_time'].isoformat()
        
        # Convert enum values to strings
        if 'location_type' in update_dict:
            update_dict['location_type'] = update_dict['location_type'].value
        
        if 'status' in update_dict:
            update_dict['status'] = update_dict['status'].value
        
        # Clear unused location fields if location_type is being updated
        if 'location_type' in update_dict:
            if update_dict['location_type'] == 'zoom':
                update_dict['google_meet_link'] = None
                update_dict['classroom_location'] = None
            elif update_dict['location_type'] == 'google_meet':
                update_dict['zoom_link'] = None
                update_dict['classroom_location'] = None
            elif update_dict['location_type'] == 'physical_classroom':
                update_dict['zoom_link'] = None
                update_dict['google_meet_link'] = None
        
        if update_dict:
            update_dict["updated_at"] = datetime.utcnow()
            await self.collection.update_one(
                {"_id": ObjectId(lesson_id)},
                {"$set": update_dict}
            )
        
        updated_lesson = await self.get_lesson_by_id(lesson_id)
        if updated_lesson and '_id' in updated_lesson:
            updated_lesson['_id'] = str(updated_lesson['_id'])
        return updated_lesson
    
    async def delete_lesson(self, lesson_id: str) -> bool:
        if not ObjectId.is_valid(lesson_id):
            return False
        
        # HARD DELETE - Remove the document completely from lessons collection
        result = await self.collection.delete_one(
            {"_id": ObjectId(lesson_id)}
        )
        
        # Also delete any related completions from user_lesson_completions collection
        await self.completions_collection.delete_many({
            "lesson_id": lesson_id
        })
        
        return result.deleted_count > 0
    
    async def mark_lesson_completed(self, user_id: str, lesson_id: str) -> bool:
        if not ObjectId.is_valid(lesson_id):
            return False
        
        # Check if lesson exists
        lesson = await self.get_lesson_by_id(lesson_id)
        if not lesson:
            return False
        
        # Check if already completed
        existing = await self.completions_collection.find_one({
            "user_id": user_id,
            "lesson_id": lesson_id
        })
        
        if existing:
            return False
        
        # Mark as completed
        completion_data = {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "completed_at": datetime.utcnow()
        }
        await self.completions_collection.insert_one(completion_data)
        
        # Update lesson status to completed
        await self.collection.update_one(
            {"_id": ObjectId(lesson_id)},
            {"$set": {"status": "completed", "updated_at": datetime.utcnow()}}
        )
        
        return True
    
    async def is_lesson_completed(self, user_id: str, lesson_id: str) -> bool:
        if not ObjectId.is_valid(lesson_id):
            return False
        
        completion = await self.completions_collection.find_one({
            "user_id": user_id,
            "lesson_id": lesson_id
        })
        return completion is not None
    
    async def get_user_completed_lessons(self, user_id: str, course_id: str) -> List[str]:
        cursor = self.completions_collection.find({"user_id": user_id})
        completions = await cursor.to_list(length=None)
        
        # Get lesson IDs and check if they belong to the course
        completed_lesson_ids = []
        for completion in completions:
            lesson = await self.get_lesson_by_id(completion["lesson_id"])
            if lesson and lesson.get("course_id") == course_id:
                completed_lesson_ids.append(completion["lesson_id"])
        
        return completed_lesson_ids