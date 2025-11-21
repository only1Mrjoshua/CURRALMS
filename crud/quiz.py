from database import get_database
from schemas.quiz import QuizCreate, QuestionCreate, QuizCategoryEnum
from typing import List, Optional, Dict, Any
import datetime
import uuid
import re

class QuizCRUD:
    
    async def create_quiz(self, quiz_data: QuizCreate) -> Dict[str, Any]:
        db = await get_database()
        
        quiz_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow()
        
        quiz_doc = {
            "_id": quiz_id,
            "course_id": quiz_data.course_id,
            "title": quiz_data.title,
            "description": quiz_data.description,
            "category": quiz_data.category.value if hasattr(quiz_data.category, 'value') else quiz_data.category,
            "total_questions": quiz_data.total_questions,
            "passing_score": quiz_data.passing_score,
            "created_at": now,
            "updated_at": now
        }
        
        # Insert quiz
        await db.quizzes.insert_one(quiz_doc)
        
        # Insert questions
        questions = []
        for q_data in quiz_data.questions:
            question_id = str(uuid.uuid4())
            question_doc = {
                "_id": question_id,
                "quiz_id": quiz_id,
                "question_text": q_data.question_text,
                "question_type": q_data.question_type,
                "options": q_data.options,
                "correct_answer": q_data.correct_answer,
                "code_template": q_data.code_template,
                "test_cases": q_data.test_cases,
                "created_at": now
            }
            questions.append(question_doc)
        
        if questions:
            await db.quiz_questions.insert_many(questions)
        
        # Return the created quiz with questions
        quiz_doc["id"] = quiz_doc.pop("_id")
        return quiz_doc
    
    async def get_quiz_by_id(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        db = await get_database()
        quiz = await db.quizzes.find_one({"_id": quiz_id})
        if quiz:
            quiz["id"] = quiz.pop("_id")
            # Add default category if missing for existing quizzes
            if "category" not in quiz:
                quiz["category"] = "other"
        return quiz
    
    async def get_all_quizzes(self) -> List[Dict[str, Any]]:
        db = await get_database()
        quizzes = await db.quizzes.find().to_list(length=1000)
        for quiz in quizzes:
            quiz["id"] = quiz.pop("_id")
            # Add default category if missing for existing quizzes
            if "category" not in quiz:
                quiz["category"] = "other"
        return quizzes
    
    async def get_quiz_questions(self, quiz_id: str) -> List[Dict[str, Any]]:
        db = await get_database()
        questions = await db.quiz_questions.find({"quiz_id": quiz_id}).to_list(length=100)
        for question in questions:
            question["id"] = question.pop("_id")
        return questions
    
    async def update_quiz(self, quiz_id: str, quiz_data: QuizCreate) -> Optional[Dict[str, Any]]:
        db = await get_database()
        
        # Check if quiz exists
        existing_quiz = await db.quizzes.find_one({"_id": quiz_id})
        if not existing_quiz:
            return None
        
        now = datetime.datetime.utcnow()
        
        # Update quiz
        update_data = {
            "course_id": quiz_data.course_id,
            "title": quiz_data.title,
            "description": quiz_data.description,
            "category": quiz_data.category.value if hasattr(quiz_data.category, 'value') else quiz_data.category,
            "total_questions": quiz_data.total_questions,
            "passing_score": quiz_data.passing_score,
            "updated_at": now
        }
        
        await db.quizzes.update_one(
            {"_id": quiz_id},
            {"$set": update_data}
        )
        
        # Delete existing questions and create new ones
        await db.quiz_questions.delete_many({"quiz_id": quiz_id})
        
        # Insert new questions
        questions = []
        for q_data in quiz_data.questions:
            question_id = str(uuid.uuid4())
            question_doc = {
                "_id": question_id,
                "quiz_id": quiz_id,
                "question_text": q_data.question_text,
                "question_type": q_data.question_type,
                "options": q_data.options,
                "correct_answer": q_data.correct_answer,
                "code_template": q_data.code_template,
                "test_cases": q_data.test_cases,
                "created_at": now
            }
            questions.append(question_doc)
        
        if questions:
            await db.quiz_questions.insert_many(questions)
        
        # Return updated quiz
        updated_quiz = await db.quizzes.find_one({"_id": quiz_id})
        if updated_quiz:
            updated_quiz["id"] = updated_quiz.pop("_id")
            # Add default category if missing for existing quizzes
            if "category" not in updated_quiz:
                updated_quiz["category"] = "other"
        return updated_quiz
    
    async def delete_quiz(self, quiz_id: str) -> bool:
        db = await get_database()
        
        # Check if quiz exists
        existing_quiz = await db.quizzes.find_one({"_id": quiz_id})
        if not existing_quiz:
            return False
        
        # Delete quiz and related data
        await db.quizzes.delete_one({"_id": quiz_id})
        await db.quiz_questions.delete_many({"quiz_id": quiz_id})
        await db.user_quiz_completions.delete_many({"quiz_id": quiz_id})
        
        return True
    
    async def create_quiz_completion(self, user_id: str, quiz_id: str, score: float, 
                                   passed: bool, detailed_results: List[Dict]) -> Dict[str, Any]:
        db = await get_database()
        
        # Get attempt number
        previous_attempts = await db.user_quiz_completions.count_documents({
            "user_id": user_id, 
            "quiz_id": quiz_id
        })
        attempt_number = previous_attempts + 1
        
        completion_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow()
        
        completion_doc = {
            "_id": completion_id,
            "user_id": user_id,
            "quiz_id": quiz_id,
            "score": score,
            "attempt_number": attempt_number,
            "passed": passed,
            "detailed_results": detailed_results,
            "completed_at": now
        }
        
        await db.user_quiz_completions.insert_one(completion_doc)
        
        completion_doc["id"] = completion_doc.pop("_id")
        return completion_doc
    
    async def get_quiz_completions(self, quiz_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = await get_database()
        
        query = {"quiz_id": quiz_id}
        if user_id:
            query["user_id"] = user_id
        
        completions = await db.user_quiz_completions.find(query).to_list(length=100)
        for completion in completions:
            completion["id"] = completion.pop("_id")
        return completions
    
    async def get_user_quiz_history(self, user_id: str) -> List[Dict[str, Any]]:
        db = await get_database()
        completions = await db.user_quiz_completions.find({"user_id": user_id}).to_list(length=100)
        for completion in completions:
            completion["id"] = completion.pop("_id")
        return completions

    async def get_quizzes_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all quizzes by category"""
        try:
            db = await get_database()
            
            # Normalize category name
            normalized_category = self.normalize_category_name(category)
            
            # Try exact match first, then case-insensitive match
            quizzes = await db.quizzes.find({
                "category": {"$regex": f"^{re.escape(normalized_category)}$", "$options": "i"}
            }).to_list(length=100)
            
            # Convert _id to id for response and ensure category exists
            for quiz in quizzes:
                quiz["id"] = str(quiz["_id"])
                del quiz["_id"]
                # Add default category if missing for existing quizzes
                if "category" not in quiz:
                    quiz["category"] = "other"
            
            print(f"Found {len(quizzes)} quizzes for category: {category} (normalized: {normalized_category})")
            return quizzes
            
        except Exception as e:
            print(f"Error getting quizzes by category: {e}")
            return []

    def normalize_category_name(self, category: str) -> str:
        """Normalize category names for consistent matching"""
        category_map = {
            'cybersecurity': 'cyber security',
            'web dev': 'web development',
            'ui/ux': 'design',
            'ui ux': 'design',
            'ai ml': 'ai & machine learning',
            'ai/ml': 'ai & machine learning',
            'ai & ml': 'ai & machine learning',
            'crypto': 'cryptocurrency',
        }
        
        normalized = category.lower().strip()
        return category_map.get(normalized, normalized)

    async def get_quiz_categories(self) -> List[str]:
        """Get all unique quiz categories"""
        try:
            db = await get_database()
            categories = await db.quizzes.distinct("category")
            
            # Add default category if no categories exist yet
            if not categories:
                categories = ["other"]
            
            return sorted([cat for cat in categories if cat])
            
        except Exception as e:
            print(f"Error getting quiz categories: {e}")
            return ["other"]

    async def search_quizzes(self, search_term: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search quizzes by title, description, and optionally filter by category"""
        try:
            db = await get_database()
            
            query = {}
            
            # Add search term filter
            if search_term:
                query["$or"] = [
                    {"title": {"$regex": search_term, "$options": "i"}},
                    {"description": {"$regex": search_term, "$options": "i"}}
                ]
            
            # Add category filter
            if category:
                normalized_category = self.normalize_category_name(category)
                query["category"] = {"$regex": f"^{re.escape(normalized_category)}$", "$options": "i"}
            
            quizzes = await db.quizzes.find(query).to_list(length=100)
            
            # Convert _id to id for response and ensure category exists
            for quiz in quizzes:
                quiz["id"] = str(quiz["_id"])
                del quiz["_id"]
                # Add default category if missing for existing quizzes
                if "category" not in quiz:
                    quiz["category"] = "other"
            
            return quizzes
            
        except Exception as e:
            print(f"Error searching quizzes: {e}")
            return []

    async def add_category_to_existing_quiz(self, quiz_id: str, category: str) -> bool:
        """Manually add category to an existing quiz"""
        try:
            db = await get_database()
            
            result = await db.quizzes.update_one(
                {"_id": quiz_id},
                {"$set": {"category": category}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error adding category to quiz: {e}")
            return False