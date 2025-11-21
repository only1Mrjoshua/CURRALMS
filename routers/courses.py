from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime

from database import get_database
from crud.course import CourseCRUD
from services.course_progression import CourseProgressionService
from schemas.course import (
    CourseResponse, CourseCreate, CourseUpdate,
    EnrollmentResponse, EnrollmentCreate, EnrollmentUpdate
)
from dependencies import (
    get_current_user, require_admin, require_student, 
    require_any_user, require_admin_or_student
)
from models.user import User, RoleEnum

router = APIRouter(prefix="/courses", tags=["courses"])

# ✅ FIXED: Simple dependency functions with no parameters
def get_course_crud():
    return CourseCRUD()

def get_progression_service():
    return CourseProgressionService()

def validate_object_id(id_str: str):
    try:
        return ObjectId(id_str)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID format")

# Course endpoints

# Create course - ADMIN ONLY
@router.post(
    "/", 
    response_model=CourseResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_course(
    course: CourseCreate,
    crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_admin)
):
    # Set the instructor_id to the current admin user if not provided
    if not course.instructor_id:
        course.instructor_id = str(current_user.id)
    
    db_course = await crud.create_course(course)
    if not db_course:
        raise HTTPException(status_code=500, detail="Failed to create course")
    return db_course

# Get all courses - ADMIN AND STUDENTS ONLY
@router.get(
    "/", 
    response_model=List[CourseResponse]
)
async def get_courses(
    crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_admin_or_student)
):
    return await crud.get_courses()

@router.get("/by-category/{category}", response_model=List[CourseResponse])
async def get_courses_by_category(
    category: str,
    crud: CourseCRUD = Depends(get_course_crud)
):
    """
    Get courses by category - ENHANCED DEBUG VERSION
    """
    print(f"🔍 ENDPOINT DEBUG: Called with category: '{category}'")
    
    try:
        print(f"🔍 ENDPOINT DEBUG: Calling CRUD method...")
        courses = await crud.get_courses_by_category(category)
        print(f"🔍 ENDPOINT DEBUG: CRUD returned {len(courses)} courses")
        
        if len(courses) == 0:
            print(f"🔍 ENDPOINT DEBUG: No courses found for category '{category}'")
            print(f"🔍 ENDPOINT DEBUG: Let me check what's in the database...")
            
            # Get ALL courses to see what categories exist
            all_courses = await crud.get_courses()
            print(f"🔍 ENDPOINT DEBUG: Total courses in database: {len(all_courses)}")
            
            # Print all unique categories
            categories_found = set()
            for course in all_courses:
                if hasattr(course, 'category') and course.category:
                    categories_found.add(course.category)
                print(f"🔍 ENDPOINT DEBUG: Course: '{course.title}' | Category: '{getattr(course, 'category', 'NO CATEGORY')}' | Active: {getattr(course, 'is_active', 'NO FIELD')}")
            
            print(f"🔍 ENDPOINT DEBUG: All categories found: {list(categories_found)}")
            
            # Check if our requested category exists in any form
            category_lower = category.lower()
            matching_categories = [cat for cat in categories_found if cat and category_lower in cat.lower()]
            print(f"🔍 ENDPOINT DEBUG: Categories similar to '{category}': {matching_categories}")
        
        else:
            for i, course in enumerate(courses):
                print(f"🔍 ENDPOINT DEBUG: Course {i+1}: '{course.title}' | Category: '{course.category}' | Active: {getattr(course, 'is_active', 'NO FIELD')}")
        
        return courses
    except Exception as e:
        print(f"❌ ENDPOINT DEBUG: Error in endpoint: {e}")
        import traceback
        print(f"❌ ENDPOINT DEBUG: Traceback: {traceback.format_exc()}")
        raise e

# Get course by ID - EVERYONE
@router.get(
    "/{course_id}", 
    response_model=CourseResponse
)
async def get_course(
    course_id: str,
    crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_any_user)
):
    validate_object_id(course_id)
    db_course = await crud.get_course(course_id)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if (current_user.role == RoleEnum.instructor and 
        db_course.instructor_id != str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view courses assigned to you"
        )
    
    return db_course

# Update course - ADMIN ONLY
@router.put(
    "/{course_id}", 
    response_model=CourseResponse
)
async def update_course(
    course_id: str,
    course_update: CourseUpdate,
    crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_admin)
):
    validate_object_id(course_id)
    db_course = await crud.update_course(course_id, course_update)
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db_course

# Delete course - ADMIN ONLY
@router.delete(
    "/{course_id}", 
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_course(
    course_id: str,
    crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_admin)
):
    validate_object_id(course_id)
    if not await crud.delete_course(course_id):
        raise HTTPException(status_code=404, detail="Course not found")

# Enrollment endpoints

@router.post("/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_course(
    enrollment: EnrollmentCreate,
    current_user: User = Depends(get_current_user),
    progression_service: CourseProgressionService = Depends(get_progression_service),
    course_crud: CourseCRUD = Depends(get_course_crud)
):
    """Enroll current user in a course"""
    try:
        # Check if user can enroll
        can_enroll, message = await progression_service.can_enroll_in_course(
            str(current_user.id), enrollment.course_id
        )
        
        if not can_enroll:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # Create enrollment
        enrollment_data = EnrollmentCreate(
            user_id=str(current_user.id),
            course_id=enrollment.course_id
        )
        
        created_enrollment = await course_crud.create_enrollment(enrollment_data)
        if not created_enrollment:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create enrollment"
            )

        return created_enrollment

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error enrolling in course: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during enrollment"
        )

# Get user enrollments - EVERYONE
@router.get(
    "/enrollments/user/{user_id}", 
    response_model=List[EnrollmentResponse]
)
async def get_user_enrollments(
    user_id: str,
    crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_any_user)
):
    validate_object_id(user_id)
    
    if current_user.role == RoleEnum.student and user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own enrollments"
        )
    
    enrollments = await crud.get_user_enrollments(user_id)
    
    if current_user.role == RoleEnum.instructor:
        filtered_enrollments = []
        for enrollment in enrollments:
            course = await crud.get_course(enrollment.course_id)
            if course and course.instructor_id == str(current_user.id):
                filtered_enrollments.append(enrollment)
        return filtered_enrollments
    
    return enrollments

# Get course enrollments - EVERYONE
@router.get(
    "/enrollments/course/{course_id}", 
    response_model=List[EnrollmentResponse]
)
async def get_course_enrollments(
    course_id: str,
    crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_any_user)
):
    validate_object_id(course_id)
    
    course = await crud.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if (current_user.role == RoleEnum.instructor and 
        course.instructor_id != str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view enrollments for courses you teach"
        )
    
    if current_user.role == RoleEnum.student:
        user_enrollments = await crud.get_user_enrollments(str(current_user.id))
        user_enrolled = any(
            enroll.course_id == course_id for enroll in user_enrollments
        )
        if not user_enrolled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view enrollments for courses you're enrolled in"
            )
    
    return await crud.get_course_enrollments(course_id)