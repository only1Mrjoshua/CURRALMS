from fastapi import APIRouter, HTTPException, Depends
from crud.quiz import QuizCRUD
from services.grading import GradingService
from services.progress_service import ProgressService
from schemas.quiz import (
    QuizCreate, QuizResponse, QuizSubmission, QuizResult,
    QuizProgressResponse, UserQuizHistoryResponse
)
from dependencies import (
    get_current_user, require_admin, require_instructor_or_admin,
    require_student, require_any_user
)
from models.user import User, RoleEnum
from schemas.quiz import QuestionTypeEnum
from database import get_database

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])

quiz_crud = QuizCRUD()
grading_service = GradingService()
progress_service = ProgressService()

@router.post("/", response_model=QuizResponse)
async def create_quiz(
    quiz: QuizCreate,
    current_user: User = Depends(require_instructor_or_admin)
):
    """Create a new quiz - Only instructors and admins"""
    return await quiz_crud.create_quiz(quiz)

@router.get("/", response_model=list[QuizResponse])
async def get_quizzes(
    current_user: User = Depends(require_any_user)
):
    """Get all quizzes - Accessible to all authenticated users"""
    return await quiz_crud.get_all_quizzes()

@router.get("/{quiz_id}/questions")
async def get_quiz_questions(
    quiz_id: str,
    current_user: User = Depends(require_any_user)
):
    """Get all questions for a specific quiz - Accessible to all authenticated users"""
    # Verify quiz exists
    quiz = await quiz_crud.get_quiz_by_id(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get questions
    questions = await quiz_crud.get_quiz_questions(quiz_id)
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this quiz")
    
    # For students, we might want to exclude correct answers
    # For instructors/admins, show everything
    if current_user.role == RoleEnum.student:
        # Remove correct answers for students (unless it's after submission)
        for question in questions:
            if "correct_answer" in question:
                del question["correct_answer"]
            if "test_cases" in question:
                # Keep test cases but remove expected outputs for coding questions
                for test_case in question.get("test_cases", []):
                    if "expected_output" in test_case:
                        del test_case["expected_output"]
    
    return {
        "quiz_id": quiz_id,
        "quiz_title": quiz.get("title"),
        "total_questions": len(questions),
        "questions": questions
    }


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    current_user: User = Depends(require_any_user)
):
    """Get specific quiz by ID - Accessible to all authenticated users"""
    quiz = await quiz_crud.get_quiz_by_id(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz

@router.post("/{quiz_id}/submit", response_model=QuizResult)
async def submit_quiz(
    quiz_id: str,
    submission: QuizSubmission,
    current_user: User = Depends(require_student)
):
    """Submit quiz answers - Only students"""
    # Get quiz
    quiz = await quiz_crud.get_quiz_by_id(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get questions
    questions = await quiz_crud.get_quiz_questions(quiz_id)
    if not questions:
        raise HTTPException(status_code=400, detail="No questions available for this quiz")
    
    correct_count = 0
    detailed_results = []
    
    # Grade each question
    for question in questions:
        user_answer = submission.answers.get(question["id"])
        
        if user_answer is None:
            detailed_results.append({
                "question_id": question["id"],
                "question_type": question["question_type"],
                "result": "unanswered"
            })
            continue
        
        # Grade based on question type
        grade_result = grading_service.grade_question(
            question_type=question["question_type"],
            user_answer=user_answer,
            correct_answer=question["correct_answer"],
            test_cases=question.get("test_cases", [])
        )
        
        if question["question_type"] in [QuestionTypeEnum.multiple_choice, QuestionTypeEnum.true_false]:
            if grade_result['correct']:
                correct_count += 1
                detailed_results.append({
                    "question_id": question["id"],
                    "question_type": question["question_type"],
                    "result": "correct"
                })
            else:
                detailed_results.append({
                    "question_id": question["id"],
                    "question_type": question["question_type"],
                    "result": "incorrect"
                })
        
        elif question["question_type"] == QuestionTypeEnum.coding:
            if grade_result['passed']:
                correct_count += 1
            
            detailed_results.append({
                "question_id": question["id"],
                "question_type": question["question_type"],
                "result": "passed" if grade_result['passed'] else "failed",
                "details": grade_result.get('details')
            })
    
    # Calculate score
    score = (correct_count / len(questions)) * 100
    passed = score >= quiz["passing_score"]
    
    # Record completion
    completion = await quiz_crud.create_quiz_completion(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=score,
        passed=passed,
        detailed_results=detailed_results
    )
    
    # Update course progress after quiz completion
    progress = await progress_service.update_course_progress_after_quiz(
        current_user.id, quiz_id
    )
    
    return QuizResult(
        quiz_id=quiz_id,
        user_id=current_user.id,
        score=round(score, 2),
        passed=passed,
        completed_at=completion["completed_at"],
        detailed_results=detailed_results,
        progress=progress
    )

@router.get("/{quiz_id}/progress", response_model=list[QuizProgressResponse])
async def get_quiz_progress(
    quiz_id: str,
    current_user: User = Depends(require_any_user)
):
    """Get progress for a specific quiz"""
    quiz = await quiz_crud.get_quiz_by_id(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Students can only see their own progress
    # Admins/Instructors can see all progress
    if current_user.role == RoleEnum.student:
        completions = await quiz_crud.get_quiz_completions(quiz_id, current_user.id)
    else:
        completions = await quiz_crud.get_quiz_completions(quiz_id)
    
    response = []
    for completion in completions:
        # Get course title if available (you might need to fetch from courses collection)
        course_title = None
        try:
            from database import get_database
            db = await get_database()
            course = await db.courses.find_one({"_id": quiz["course_id"]})
            if course:
                course_title = course.get("title")
        except:
            course_title = None
        
        response.append(QuizProgressResponse(
            id=completion["id"],
            user_id=completion["user_id"],
            quiz_id=completion["quiz_id"],
            quiz_title=quiz["title"],
            course_title=course_title,  # Now this is provided
            score=completion["score"],
            attempt_number=completion["attempt_number"],
            passed=completion["passed"],
            completed_at=completion["completed_at"]
        ))
    
    return response

@router.get("/users/{user_id}/progress", response_model=UserQuizHistoryResponse)
async def get_user_quiz_progress(
    user_id: str,
    current_user: User = Depends(require_instructor_or_admin)
):
    """Get quiz progress for a specific user - Only instructors and admins"""
    completions = await quiz_crud.get_user_quiz_history(user_id)
    stats = await progress_service.get_user_quiz_stats(user_id)
    
    progress_list = []
    for completion in completions:
        quiz = await quiz_crud.get_quiz_by_id(completion["quiz_id"])
        progress_list.append(QuizProgressResponse(
            id=completion["id"],
            user_id=completion["user_id"],
            quiz_id=completion["quiz_id"],
            quiz_title=quiz["title"] if quiz else None,
            score=completion["score"],
            attempt_number=completion["attempt_number"],
            passed=completion["passed"],
            completed_at=completion["completed_at"]
        ))
    
    return UserQuizHistoryResponse(
        user_id=user_id,
        summary=stats,
        progress=progress_list
    )

@router.put("/{quiz_id}", response_model=QuizResponse)
async def update_quiz(
    quiz_id: str,
    updated_quiz: QuizCreate,
    current_user: User = Depends(require_instructor_or_admin)
):
    """Update a quiz - Only instructors and admins"""
    quiz = await quiz_crud.update_quiz(quiz_id, updated_quiz)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz

@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    current_user: User = Depends(require_instructor_or_admin)
):
    """Delete a quiz - Only instructors and admins"""
    success = await quiz_crud.delete_quiz(quiz_id)
    if not success:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return {"message": "Quiz deleted successfully"}


@router.get("/{quiz_id}/debug")
async def debug_quiz(quiz_id: str, current_user: User = Depends(require_any_user)):
    """Debug endpoint to see quiz structure"""
    quiz = await quiz_crud.get_quiz_by_id(quiz_id)
    questions = await quiz_crud.get_quiz_questions(quiz_id)
    
    question_details = []
    for q in questions:
        question_details.append({
            "id": q["id"],
            "question_text": q["question_text"],
            "question_type": q["question_type"],
            "correct_answer": q["correct_answer"],
            "options": q.get("options", [])
        })
    
    return {
        "quiz": quiz,
        "questions": question_details
    }

@router.get("/category/{category}", response_model=list[QuizResponse])
async def get_quizzes_by_category(
    category: str,
    current_user: User = Depends(require_any_user)
):
    """Get all quizzes by category - Accessible to all authenticated users"""
    quizzes = await quiz_crud.get_quizzes_by_category(category)
    
    if not quizzes:
        raise HTTPException(
            status_code=404, 
            detail=f"No quizzes found for category: {category}"
        )
    
    return quizzes