from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from bson import ObjectId

from database import get_database
from dependencies import get_current_user, require_admin, require_instructor_or_admin, require_any_user
from models.lesson import LessonCreate, LessonUpdate, LessonOut, LessonWithCompletion, LessonWithCourseOut
from models.user import User
from crud.lesson import LessonCRUD
from crud.course import CourseCRUD

router = APIRouter(prefix="/lessons", tags=["Lessons"])

def get_lesson_crud(db=Depends(get_database)):
    return LessonCRUD(db)

def get_course_crud(db=Depends(get_database)):
    return CourseCRUD()

# ---------- CREATE LESSON ----------
@router.post("/", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson: LessonCreate,
    crud: LessonCRUD = Depends(get_lesson_crud),
    course_crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_instructor_or_admin)
):
    # Validate course exists
    course = await course_crud.get_course(lesson.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user is instructor of this course (if not admin)
    if current_user.role != "admin":
        if str(course.instructor_id) != str(current_user.id):
            raise HTTPException(
                status_code=403, 
                detail="You are not the instructor for this course"
            )
    
    try:
        new_lesson = await crud.create_lesson(lesson, str(current_user.id))
        
        if not new_lesson:
            raise HTTPException(status_code=500, detail="Failed to create lesson")
        
        return LessonOut(**new_lesson)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error creating lesson: {str(e)}"
        )

# ---------- GET LESSONS FOR A COURSE ----------
@router.get("/course/{course_id}", response_model=List[LessonOut])
async def get_lessons_for_course(
    course_id: str,
    include_inactive: bool = False,
    crud: LessonCRUD = Depends(get_lesson_crud),
    current_user: User = Depends(require_any_user)
):
    if not ObjectId.is_valid(course_id):
        raise HTTPException(status_code=400, detail="Invalid course ID")
    
    lessons = await crud.get_lessons_by_course(course_id, include_inactive)
    if not lessons:
        return []
    
    lesson_responses = []
    for lesson in lessons:
        lesson_responses.append(LessonOut(**lesson))
    
    return lesson_responses

# ---------- GET LESSONS BY CATEGORY (FIXED) ----------
@router.get("/category/{category}", response_model=List[LessonOut])
async def get_lessons_by_category(
    category: str,
    include_inactive: bool = False,
    crud: LessonCRUD = Depends(get_lesson_crud),
    current_user: User = Depends(require_any_user)
):
    """Get lessons by category - FIXED VERSION"""
    print(f"🔍 ROUTER DEBUG: Getting lessons for category: '{category}'")
    
    lessons = await crud.get_lessons_by_category(category, include_inactive)
    
    print(f"🔍 ROUTER DEBUG: Found {len(lessons) if lessons else 0} lessons for category '{category}'")
    
    if not lessons:
        return []
    
    lesson_responses = []
    for lesson in lessons:
        lesson_responses.append(LessonOut(**lesson))
    
    return lesson_responses

# ---------- GET UPCOMING LESSONS ----------
@router.get("/upcoming/", response_model=List[LessonOut])
async def get_upcoming_lessons(
    limit: int = Query(10, ge=1, le=50),
    crud: LessonCRUD = Depends(get_lesson_crud),
    current_user: User = Depends(require_any_user)
):
    lessons = await crud.get_upcoming_lessons(limit)
    if not lessons:
        return []
    
    lesson_responses = []
    for lesson in lessons:
        lesson_responses.append(LessonOut(**lesson))
    
    return lesson_responses

# ---------- GET SINGLE LESSON ----------
@router.get("/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    lesson_id: str,
    crud: LessonCRUD = Depends(get_lesson_crud),
    current_user: User = Depends(require_any_user)
):
    if not ObjectId.is_valid(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid lesson ID")
    
    lesson = await crud.get_lesson_by_id(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    return LessonOut(**lesson)

# ---------- GET ALL LESSONS SIMPLE (NO FILTERS) ----------
@router.get("/", response_model=List[LessonOut])
async def get_all_lessons_simple(
    crud: LessonCRUD = Depends(get_lesson_crud),
    current_user: User = Depends(require_admin)
):
    """Get ALL lessons without any filtering - SIMPLE VERSION"""
    try:
        print("🔍 ROUTER DEBUG: Getting ALL lessons (simple version)")
        
        lessons = await crud.get_all_lessons_simple()
        print(f"🔍 ROUTER DEBUG: Retrieved {len(lessons) if lessons else 0} lessons")
        
        if not lessons:
            return []
        
        lesson_responses = []
        for lesson in lessons:
            lesson_responses.append(LessonOut(**lesson))
        
        print(f"🔍 ROUTER DEBUG: Returning {len(lesson_responses)} lessons")
        return lesson_responses
        
    except Exception as e:
        print(f"❌ ROUTER DEBUG: Error in get_all_lessons_simple: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving lessons: {str(e)}"
        )

# ---------- GET ALL LESSONS WITH FILTERS ----------
@router.get("/filtered/", response_model=List[LessonOut])
async def get_all_lessons_filtered(
    course_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    crud: LessonCRUD = Depends(get_lesson_crud),
    current_user: User = Depends(require_admin)
):
    """Get all lessons with optional filtering"""
    try:
        # Convert status string to enum if provided
        lesson_status = None
        if status:
            try:
                from models.lesson import LessonStatus
                lesson_status = LessonStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status value")
        
        lessons = await crud.get_all_lessons(
            course_id=course_id,
            category=category,
            status=lesson_status
        )
        
        if not lessons:
            return []
        
        lesson_responses = []
        for lesson in lessons:
            lesson_responses.append(LessonOut(**lesson))
        
        return lesson_responses
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving lessons: {str(e)}"
        )

# ---------- UPDATE LESSON ----------
@router.put("/{lesson_id}", response_model=LessonOut)
async def update_lesson(
    lesson_id: str,
    updated: LessonUpdate,
    crud: LessonCRUD = Depends(get_lesson_crud),
    course_crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_instructor_or_admin)
):
    if not ObjectId.is_valid(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid lesson ID")
    
    existing_lesson = await crud.get_lesson_by_id(lesson_id)
    if not existing_lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    if current_user.role != "admin":
        course = await course_crud.get_course(existing_lesson['course_id'])
        if not course or str(course.instructor_id) != str(current_user.id):
            raise HTTPException(
                status_code=403, 
                detail="You are not the instructor for this course"
            )
    
    updated_lesson = await crud.update_lesson(lesson_id, updated)
    if not updated_lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    return LessonOut(**updated_lesson)

# ---------- DELETE LESSON (SOFT DELETE) ----------
@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: str,
    crud: LessonCRUD = Depends(get_lesson_crud),
    course_crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_instructor_or_admin)
):
    if not ObjectId.is_valid(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid lesson ID")
    
    existing_lesson = await crud.get_lesson_by_id(lesson_id)
    if not existing_lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    if current_user.role != "admin":
        course = await course_crud.get_course(existing_lesson['course_id'])
        if not course or str(course.instructor_id) != str(current_user.id):
            raise HTTPException(
                status_code=403, 
                detail="You are not the instructor for this course"
            )
    
    success = await crud.delete_lesson(lesson_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    return {"detail": "Lesson deleted successfully"}

# ---------- COMPLETE LESSON ----------
@router.post("/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: str,
    crud: LessonCRUD = Depends(get_lesson_crud),
    current_user: User = Depends(require_any_user)
):
    if not ObjectId.is_valid(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid lesson ID")
    
    lesson = await crud.get_lesson_by_id(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    success = await crud.mark_lesson_completed(str(current_user.id), lesson_id)
    if not success:
        raise HTTPException(status_code=400, detail="Lesson already completed")
    
    return {"message": "Lesson marked as completed"}