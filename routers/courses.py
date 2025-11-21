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
    
    course_data = await crud.create_course(course)
    if not course_data:
        raise HTTPException(status_code=500, detail="Failed to create course")
    
    # Convert dict to CourseResponse
    return CourseResponse(**course_data)

# Get all courses - ADMIN AND STUDENTS ONLY
@router.get(
    "/", 
    response_model=List[CourseResponse]
)
async def get_courses(
    crud: CourseCRUD = Depends(get_course_crud),
    current_user: User = Depends(require_admin_or_student)
):
    courses_data = await crud.get_courses()
    # Convert dicts to CourseResponse objects
    return [CourseResponse(**course_data) for course_data in courses_data]

@router.get("/by-category/{category}", response_model=List[CourseResponse])
async def get_courses_by_category(
    category: str,
    crud: CourseCRUD = Depends(get_course_crud)
):
    """
    Get courses by category - FIXED VERSION
    """
    print(f"🔍 ENDPOINT DEBUG: Called with category: '{category}'")
    
    try:
        print(f"🔍 ENDPOINT DEBUG: Calling CRUD method...")
        courses_data = await crud.get_courses_by_category(category)
        print(f"🔍 ENDPOINT DEBUG: CRUD returned {len(courses_data)} courses")
        
        if len(courses_data) == 0:
            print(f"🔍 ENDPOINT DEBUG: No courses found for category '{category}'")
            print(f"🔍 ENDPOINT DEBUG: Let me check what's in the database...")
            
            # Get ALL courses to see what categories exist
            all_courses_data = await crud.get_courses()
            print(f"🔍 ENDPOINT DEBUG: Total courses in database: {len(all_courses_data)}")
            
            # Print all unique categories
            categories_found = set()
            for course_data in all_courses_data:
                if course_data.get('category'):
                    categories_found.add(course_data['category'])
                print(f"🔍 ENDPOINT DEBUG: Course: '{course_data.get('title', 'No title')}' | Category: '{course_data.get('category', 'NO CATEGORY')}' | Active: {course_data.get('is_active', 'NO FIELD')}")
            
            print(f"🔍 ENDPOINT DEBUG: All categories found: {list(categories_found)}")
            
            # Check if our requested category exists in any form
            category_lower = category.lower()
            matching_categories = [cat for cat in categories_found if cat and category_lower in cat.lower()]
            print(f"🔍 ENDPOINT DEBUG: Categories similar to '{category}': {matching_categories}")
            
            return []
        
        # Convert dicts to CourseResponse objects
        courses = [CourseResponse(**course_data) for course_data in courses_data]
        
        for i, course in enumerate(courses):
            print(f"🔍 ENDPOINT DEBUG: Course {i+1}: '{course.title}' | Category: '{course.category}' | Active: {course.is_active}")
        
        return courses
    except Exception as e:
        print(f"❌ ENDPOINT DEBUG: Error in endpoint: {e}")
        import traceback
        print(f"❌ ENDPOINT DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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
    course_data = await crud.get_course(course_id)
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Convert dict to CourseResponse
    course = CourseResponse(**course_data)
    
    if (current_user.role == RoleEnum.instructor and 
        course.instructor_id != str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view courses assigned to you"
        )
    
    return course

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
    course_data = await crud.update_course(course_id, course_update)
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Convert dict to CourseResponse
    return CourseResponse(**course_data)

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
        
        enrollment_dict = await course_crud.create_enrollment(enrollment_data)
        if not enrollment_dict:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create enrollment"
            )

        # Convert dict to EnrollmentResponse
        return EnrollmentResponse(**enrollment_dict)

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
    
    enrollments_data = await crud.get_user_enrollments(user_id)
    
    if current_user.role == RoleEnum.instructor:
        filtered_enrollments = []
        for enrollment_data in enrollments_data:
            course_data = await crud.get_course(enrollment_data['course_id'])
            if course_data and course_data.get('instructor_id') == str(current_user.id):
                filtered_enrollments.append(EnrollmentResponse(**enrollment_data))
        return filtered_enrollments
    
    # Convert dicts to EnrollmentResponse objects
    return [EnrollmentResponse(**enrollment_data) for enrollment_data in enrollments_data]

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
    
    course_data = await crud.get_course(course_id)
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course = CourseResponse(**course_data)
    
    if (current_user.role == RoleEnum.instructor and 
        course.instructor_id != str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view enrollments for courses you teach"
        )
    
    if current_user.role == RoleEnum.student:
        user_enrollments_data = await crud.get_user_enrollments(str(current_user.id))
        user_enrolled = any(
            enroll_data['course_id'] == course_id for enroll_data in user_enrollments_data
        )
        if not user_enrolled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view enrollments for courses you're enrolled in"
            )
    
    enrollments_data = await crud.get_course_enrollments(course_id)
    # Convert dicts to EnrollmentResponse objects
    return [EnrollmentResponse(**enrollment_data) for enrollment_data in enrollments_data]