from typing import Tuple, Optional
from crud.course import CourseCRUD


class CourseProgressionService:
    def __init__(self):
        # ✅ FIXED: No database parameter
        self.course_crud = CourseCRUD()

    async def can_enroll_in_course(self, user_id: str, course_id: str) -> Tuple[bool, str]:
        """Check if a user can enroll in a course"""
        try:
            # Get the course using the correct method name
            course = await self.course_crud.get_course(course_id)
            if not course:
                return False, "Course not found"

            # Check if user is already enrolled
            enrollments = await self.course_crud.get_user_enrollments(user_id)
            for enrollment in enrollments:
                if enrollment.course_id == course_id:
                    return False, "Already enrolled in this course"

            return True, "Can enroll"
            
        except Exception as e:
            print(f"Error checking enrollment eligibility: {e}")
            return False, f"Error: {str(e)}"

    async def get_user_progress(self, user_id: str, course_id: str) -> Optional[dict]:
        """Get user progress for a course"""
        try:
            enrollments = await self.course_crud.get_user_enrollments(user_id)
            for enrollment in enrollments:
                if enrollment.course_id == course_id:
                    return {
                        "progress_percentage": enrollment.progress_percentage,
                        "current_lesson_id": enrollment.current_lesson_id,
                        "completed_lessons": enrollment.completed_lessons,
                        "status": enrollment.status
                    }
            return None
        except Exception as e:
            print(f"Error getting user progress: {e}")
            return None

    async def update_progress(self, user_id: str, course_id: str, lesson_id: str) -> bool:
        """Update user progress when they complete a lesson"""
        try:
            enrollments = await self.course_crud.get_user_enrollments(user_id)
            for enrollment in enrollments:
                if enrollment.course_id == course_id:
                    # Add lesson to completed lessons if not already there
                    if lesson_id not in enrollment.completed_lessons:
                        updated_completed_lessons = enrollment.completed_lessons + [lesson_id]
                        
                        # Calculate new progress percentage
                        total_lessons = 10  # Placeholder
                        new_progress = min(100.0, (len(updated_completed_lessons) / total_lessons) * 100)
                        
                        # Update enrollment
                        from schemas.course import EnrollmentUpdate
                        update_data = EnrollmentUpdate(
                            completed_lessons=updated_completed_lessons,
                            progress_percentage=new_progress,
                            current_lesson_id=lesson_id
                        )
                        
                        updated_enrollment = await self.course_crud.update_enrollment(
                            enrollment.id, update_data
                        )
                        return updated_enrollment is not None
            return False
        except Exception as e:
            print(f"Error updating progress: {e}")
            return False