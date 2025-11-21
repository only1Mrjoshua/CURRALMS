from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from models.course import Enrollment
from database import get_database

class EnrollmentCRUD:
    def __init__(self, db):
        self.db = db
        self.collection = db.enrollments

    async def create_enrollment(self, enrollment_data: dict) -> Optional[Enrollment]:
        enrollment_data["_id"] = ObjectId()
        enrollment_data["enrolled_at"] = enrollment_data.get("enrolled_at", datetime.utcnow())
        enrollment_data["status"] = enrollment_data.get("status", "enrolled")
        enrollment_data["progress_percentage"] = enrollment_data.get("progress_percentage", 0.0)
        enrollment_data["completed_lessons"] = enrollment_data.get("completed_lessons", [])
        enrollment_data["created_at"] = datetime.utcnow()
        enrollment_data["updated_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(enrollment_data)
        if result.inserted_id:
            return await self.get_enrollment_by_id(str(result.inserted_id))
        return None

    async def get_enrollment_by_id(self, enrollment_id: str) -> Optional[Enrollment]:
        enrollment = await self.collection.find_one({"_id": ObjectId(enrollment_id)})
        return Enrollment(**enrollment) if enrollment else None

    async def get_user_course_enrollment(self, user_id: str, course_id: str) -> Optional[Enrollment]:
        enrollment = await self.collection.find_one({
            "user_id": ObjectId(user_id),  # FIXED: Convert to ObjectId
            "course_id": ObjectId(course_id)  # FIXED: Convert to ObjectId
        })
        return Enrollment(**enrollment) if enrollment else None

    async def get_user_enrollments(self, user_id: str) -> List[Enrollment]:
        # FIXED: Convert string user_id to ObjectId for query
        enrollments = await self.collection.find({
            "user_id": ObjectId(user_id)  # FIXED: Convert to ObjectId
        }).to_list(length=100)
        return [Enrollment(**enrollment) for enrollment in enrollments]

    async def get_course_enrollments(self, course_id: str) -> List[Enrollment]:
        # FIXED: Convert string course_id to ObjectId for query
        enrollments = await self.collection.find({
            "course_id": ObjectId(course_id)  # FIXED: Convert to ObjectId
        }).to_list(length=100)
        return [Enrollment(**enrollment) for enrollment in enrollments]

    async def update_enrollment(self, enrollment_id: str, update_data: dict) -> Optional[Enrollment]:
        update_data["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(enrollment_id)},
            {"$set": update_data}
        )
        if result.modified_count:
            return await self.get_enrollment_by_id(enrollment_id)
        return None

    async def delete_enrollment(self, enrollment_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(enrollment_id)})
        return result.deleted_count > 0

    async def get_user_completed_courses(self, user_id: str) -> List[Enrollment]:
        # FIXED: Convert string user_id to ObjectId for query
        enrollments = await self.collection.find({
            "user_id": ObjectId(user_id),  # FIXED: Convert to ObjectId
            "status": "completed"
        }).to_list(length=100)
        return [Enrollment(**enrollment) for enrollment in enrollments]