from crud.quiz import QuizCRUD
from database import get_database
from typing import Dict, Any, List
import datetime

class ProgressService:
    
    def __init__(self):
        self.quiz_crud = QuizCRUD()
    
    async def get_course_progress(self, user_id: str, course_id: str) -> Dict[str, Any]:
        """
        Calculate comprehensive course progress including quizzes
        """
        db = await get_database()
        
        # Get course quizzes
        course_quizzes = await db.quizzes.find({"course_id": course_id}).to_list(length=100)
        total_quizzes = len(course_quizzes)
        
        # Get completed quizzes for this user and course
        quiz_ids = [quiz["_id"] for quiz in course_quizzes]
        completed_quizzes = await db.user_quiz_completions.count_documents({
            "user_id": user_id,
            "quiz_id": {"$in": quiz_ids}
        })
        
        # Calculate quiz progress (should not exceed 100%)
        quiz_progress_percentage = min(100, (completed_quizzes / total_quizzes) * 100) if total_quizzes > 0 else 0
        
        # Get course enrollment progress
        enrollment = await db.enrollments.find_one({
            "user_id": user_id,
            "course_id": course_id
        })
        
        # If no enrollment exists, create one
        if not enrollment:
            enrollment_data = {
                "user_id": user_id,
                "course_id": course_id,
                "progress_percentage": 0,
                "status": "in_progress",
                "enrolled_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow()
            }
            await db.enrollments.insert_one(enrollment_data)
            enrollment = enrollment_data
        
        lesson_progress = enrollment.get("progress_percentage", 0)
        enrollment_status = enrollment.get("status", "in_progress")
        
        # Calculate overall progress (average of lesson progress and quiz progress)
        # Ensure it doesn't exceed 100%
        if total_quizzes > 0:
            overall_progress = min(100, (lesson_progress + quiz_progress_percentage) / 2)
        else:
            overall_progress = min(100, lesson_progress)
        
        # Update status based on progress
        if overall_progress >= 100:
            enrollment_status = "completed"
        elif overall_progress > 0:
            enrollment_status = "in_progress"
        else:
            enrollment_status = "not_started"
        
        # Update enrollment with new progress and status
        await db.enrollments.update_one(
            {"user_id": user_id, "course_id": course_id},
            {"$set": {
                "progress_percentage": overall_progress,
                "status": enrollment_status,
                "updated_at": datetime.datetime.utcnow()
            }}
        )
        
        return {
            'user_id': user_id,
            'course_id': course_id,
            'overall_progress': round(overall_progress, 2),
            'lesson_progress': round(lesson_progress, 2),
            'quiz_progress': round(quiz_progress_percentage, 2),
            'completed_quizzes': completed_quizzes,
            'total_quizzes': total_quizzes,
            'status': enrollment_status
        }
    
    async def update_course_progress_after_quiz(self, user_id: str, quiz_id: str) -> Dict[str, Any]:
        """
        Update course progress when a quiz is completed
        """
        try:
            # Get quiz to find course_id
            quiz = await self.quiz_crud.get_quiz_by_id(quiz_id)
            if not quiz:
                return {"error": "Quiz not found"}
            
            course_id = quiz["course_id"]
            
            # Get current progress (this will update the enrollment)
            current_progress = await self.get_course_progress(user_id, course_id)
            
            return current_progress
            
        except Exception as e:
            return {"error": f"Failed to update progress: {str(e)}"}
    
    async def get_user_quiz_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get overall quiz statistics for a user
        """
        completions = await self.quiz_crud.get_user_quiz_history(user_id)
        
        if not completions:
            return {
                'total_quizzes_attempted': 0,
                'average_score': 0.0,
                'pass_rate': 0.0,
                'total_attempts': 0,
                'courses_with_quizzes': 0
            }
        
        total_attempts = len(completions)
        total_passed = sum(1 for c in completions if c["passed"])
        total_score = sum(c["score"] for c in completions if c.get("score") is not None)
        
        # Get unique courses with quiz attempts
        unique_courses = set()
        for completion in completions:
            quiz = await self.quiz_crud.get_quiz_by_id(completion["quiz_id"])
            if quiz and quiz.get("course_id"):
                unique_courses.add(quiz["course_id"])
        
        return {
            'total_quizzes_attempted': len(set(c["quiz_id"] for c in completions)),
            'average_score': round(total_score / total_attempts, 2) if total_attempts > 0 else 0,
            'pass_rate': round((total_passed / total_attempts) * 100, 2) if total_attempts > 0 else 0,
            'total_attempts': total_attempts,
            'courses_with_quizzes': len(unique_courses)
        }
    
    async def get_user_learning_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive learning analytics for a user
        """
        quiz_stats = await self.get_user_quiz_stats(user_id)
        
        # Get all enrolled courses progress
        db = await get_database()
        enrollments = await db.enrollments.find({"user_id": user_id}).to_list(length=100)
        
        enrolled_courses_progress = []
        for enrollment in enrollments:
            course_progress = await self.get_course_progress(user_id, enrollment["course_id"])
            enrolled_courses_progress.append(course_progress)
        
        return {
            'user_id': user_id,
            'quiz_analytics': quiz_stats,
            'course_progress': enrolled_courses_progress,
            'learning_streaks': await self._calculate_learning_streaks(user_id),
            'skill_mastery': await self._calculate_skill_mastery(user_id)
        }
    
    async def _calculate_learning_streaks(self, user_id: str) -> Dict[str, Any]:
        """Calculate learning streaks based on quiz attempts"""
        db = await get_database()
        
        # Get quiz completions in the last 30 days
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        recent_completions = await db.user_quiz_completions.find({
            "user_id": user_id,
            "completed_at": {"$gte": thirty_days_ago}
        }).to_list(length=100)
        
        # Simple streak calculation
        unique_days = set()
        for completion in recent_completions:
            completion_date = completion["completed_at"].date()
            unique_days.add(completion_date)
        
        return {
            'current_streak_days': len(unique_days),
            'total_learning_days': len(unique_days)
        }
    
    async def _calculate_skill_mastery(self, user_id: str) -> Dict[str, Any]:
        """Calculate skill mastery based on quiz performance"""
        # Placeholder implementation
        return {
            'programming': 75,
            'mathematics': 60,
            'science': 45
        }