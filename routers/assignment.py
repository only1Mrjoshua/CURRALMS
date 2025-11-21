from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import List, Optional
import os
import shutil
from datetime import datetime, timezone
import uuid
from bson import ObjectId
from database import get_database
from dependencies import get_current_user
from schemas.assignment import (
    AssignmentCreate, AssignmentUpdate, AssignmentOut,
    AssignmentSubmissionResponse, GradeSubmission,
    LateSubmissionApprovalCreate, LateSubmissionApprovalResponse,
    ExtensionRequestCreate, ExtensionRequestResponse, ExtensionRequestUpdate,
    TextSubmissionRequest, LinkSubmissionRequest, SubmissionType
)
from crud.assignment import (
    create_assignment_crud, get_assignments_by_course, get_assignment_by_id,
    update_assignment_crud, delete_assignment_crud, create_submission_crud,
    get_submission_by_user_and_assignment, get_submissions_by_assignment,
    grade_submission_crud, create_late_approval_crud, get_active_late_approval,
    create_extension_request_crud, get_extension_requests_by_assignment,
    update_extension_request_crud, get_submission_by_id, get_all_assignments
)

router = APIRouter(prefix="/assignments", tags=["Assignments"])

# Upload directory for assignment files
UPLOAD_DIR = "static/uploads/assignments"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -------------------- ASSIGNMENT CRUD -------------------- #
@router.post("/", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    assignment_data: AssignmentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new assignment (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can create assignments"
        )

    assignment = await create_assignment_crud(assignment_data.dict())
    return assignment


@router.get("/", response_model=List[AssignmentOut])
async def get_assignments(
    current_user: dict = Depends(get_current_user)
):
    """Get assignments - all for admins/instructors, enrolled courses for students"""
    if current_user.role in ["admin", "instructor"]:
        # Admins and instructors can see all assignments
        assignments = await get_all_assignments()
    else:
        # For students, get assignments from enrolled courses
        enrolled_courses = await get_enrolled_courses(current_user.id)
        if not enrolled_courses:
            return []
        
        assignments = []
        for course in enrolled_courses:
            course_assignments = await get_assignments_by_course(course)
            assignments.extend(course_assignments)
    
    return assignments


@router.get("/{assignment_id}", response_model=AssignmentOut)
async def get_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific assignment"""
    assignment = await get_assignment_by_id(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Check if student is enrolled in the course
    if current_user.role == "student":
        enrolled_courses = await get_enrolled_courses(current_user.id)
        if assignment.course_id not in enrolled_courses:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enrolled in this course"
            )

    return assignment


@router.get("/{assignment_id}/submissions/simple", response_model=List[dict])
async def get_assignment_submissions_simple(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get simple list of all submissions for an assignment (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can view submissions"
        )

    try:
        db = await get_database()
        
        print(f"🔍 [DEBUG] Using SIMPLE approach with manual joins")
        
        # Simple approach: Get submissions and manually join with users
        submissions = await db["submissions"].find({
            "assignment_id": assignment_id
        }).to_list(length=1000)
        
        print(f"🔍 [DEBUG] Found {len(submissions)} raw submissions")
        
        result = []
        for submission in submissions:
            # Get user info
            user_id = submission.get("user_id")
            user = await db["users"].find_one({"_id": ObjectId(user_id)})
            
            if user:
                submission_data = {
                    "id": str(submission["_id"]),
                    "user_id": user_id,
                    "student_name": user.get("full_name", ""),
                    "student_email": user.get("email", ""),
                    "submission_type": submission.get("submission_type", ""),
                    "content": submission.get("content", ""),
                    "file_url": submission.get("file_url"),
                    "submitted_at": submission.get("submitted_at"),
                    "grade": submission.get("grade"),
                    "is_graded": submission.get("is_graded", False),
                    "feedback": submission.get("feedback", "")
                }
                result.append(submission_data)
            else:
                print(f"⚠️ [DEBUG] User not found for user_id: {user_id}")
        
        print(f"✅ [DEBUG] Returning {len(result)} submissions with user data")
        return result

    except Exception as e:
        print(f"❌ Error fetching submissions: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch submissions"
        )


@router.put("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment(
    assignment_id: str,
    assignment_data: AssignmentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an assignment (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can update assignments"
        )

    assignment = await get_assignment_by_id(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # If course_id is being updated, handle category logic
    update_data = assignment_data.dict(exclude_unset=True)
    
    if "course_id" in update_data and update_data["course_id"] != assignment.course_id:
        print(f"🔍 [DEBUG] Course changed from {assignment.course_id} to {update_data['course_id']}")
        
        # Option 1: Automatically update category based on new course
        # You might want to fetch the new course and set category accordingly
        try:
            db = await get_database()
            new_course = await db["courses"].find_one({"_id": ObjectId(update_data["course_id"])})
            if new_course:
                # If your courses have categories, you might set it here
                # update_data["category"] = new_course.get("category", "general")
                print(f"🔍 [DEBUG] New course: {new_course.get('title', 'Unknown')}")
        except Exception as e:
            print(f"⚠️ [DEBUG] Error fetching new course info: {e}")
        
        # Option 2: Reset or handle existing submissions
        # You might want to handle what happens to existing submissions when course changes
        submissions_count = await db["submissions"].count_documents({
            "assignment_id": assignment_id
        })
        if submissions_count > 0:
            print(f"⚠️ [DEBUG] Assignment has {submissions_count} submissions that might be affected by course change")

    updated_assignment = await update_assignment_crud(
        assignment_id, 
        update_data
    )
    return updated_assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an assignment (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can delete assignments"
        )

    assignment = await get_assignment_by_id(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    await delete_assignment_crud(assignment_id)
    return


# -------------------- SEPARATE SUBMISSION ENDPOINTS -------------------- #
@router.post("/{course_id}/{assignment_id}/submit/text", response_model=AssignmentSubmissionResponse)
async def submit_text_assignment(
    course_id: str,  # Add this parameter
    assignment_id: str,
    submission_data: TextSubmissionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit a text assignment"""
    return await _create_submission(
        course_id=course_id,  # Pass course_id
        assignment_id=assignment_id,
        current_user=current_user,
        submission_type=SubmissionType.TEXT,
        content=submission_data.content,
        file_url=None
    )


@router.post("/{course_id}/{assignment_id}/submit/link", response_model=AssignmentSubmissionResponse)
async def submit_link_assignment(
    course_id: str,  # Add this parameter
    assignment_id: str,
    submission_data: LinkSubmissionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit a link assignment"""
    return await _create_submission(
        course_id=course_id,  # Pass course_id
        assignment_id=assignment_id,
        current_user=current_user,
        submission_type=SubmissionType.LINK,
        content=submission_data.content,
        file_url=None
    )


@router.post("/{course_id}/{assignment_id}/submit/file", response_model=AssignmentSubmissionResponse)
async def submit_file_assignment(
    course_id: str,  # Add this parameter
    assignment_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Submit a file assignment"""
    # Handle file upload
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_url = f"/uploads/assignments/{filename}"

    return await _create_submission(
        course_id=course_id,  # Pass course_id
        assignment_id=assignment_id,
        current_user=current_user,
        submission_type=SubmissionType.FILE,
        content=None,
        file_url=file_url
    )


# Common submission creation logic - UPDATED VERSION
async def _create_submission(
    course_id: str,
    assignment_id: str,
    current_user: dict,
    submission_type: SubmissionType,
    content: Optional[str] = None,
    file_url: Optional[str] = None
):
    """Common logic for creating submissions"""
    print(f"🔍 DEBUG: Starting submission for user {current_user.id}, course {course_id}, assignment {assignment_id}")
    
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit assignments"
        )

    # Check assignment exists
    assignment = await get_assignment_by_id(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    print(f"🔍 DEBUG: Assignment found - course_id: {assignment.course_id}")

    # Verify the course_id matches the assignment's course_id
    if assignment.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment does not belong to the specified course"
        )

    # Check if student is enrolled using the course_id from URL
    enrolled_courses = await get_enrolled_courses(current_user.id)
    print(f"🔍 DEBUG: Looking for course {course_id} in enrolled courses: {enrolled_courses}")
    
    if course_id not in enrolled_courses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enrolled in this course"
        )

    # Check for existing submission
    existing_submission = await get_submission_by_user_and_assignment(
        current_user.id, assignment_id
    )
    if existing_submission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment already submitted"
        )

    # FIX: Handle datetime comparison properly
    now = datetime.now(timezone.utc)
    
    # Make sure both datetimes are timezone-aware for comparison
    if assignment.due_date.tzinfo is None:
        # If due_date is naive, make it aware
        due_date_aware = assignment.due_date.replace(tzinfo=timezone.utc)
    else:
        due_date_aware = assignment.due_date
    
    print(f"🔍 DEBUG: Current time (UTC): {now}")
    print(f"🔍 DEBUG: Due date: {due_date_aware}")
    
    # Remove the problematic print statement that tries to compare
    # Just calculate and store the result
    is_past_due = now > due_date_aware
    print(f"🔍 DEBUG: Is past due: {is_past_due}")
    
    if is_past_due:
        # Check for late submission approval
        approval = await get_active_late_approval(current_user.id, assignment_id)
        if not approval:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment is past due date and no active late submission approval found"
            )

    # Create submission
    submission_data = {
        "user_id": current_user.id,
        "assignment_id": assignment_id,
        "submission_type": submission_type.value,
        "content": content,
        "file_url": file_url
    }
    
    submission = await create_submission_crud(submission_data)
    return submission


@router.get("/{course_id}/{assignment_id}/submissions", response_model=List[AssignmentSubmissionResponse])
async def get_assignment_submissions(
    course_id: str,  # Add this
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all submissions for an assignment (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can view submissions"
        )

    submissions = await get_submissions_by_assignment(assignment_id)
    return submissions


@router.put("/submissions/{submission_id}/grade", response_model=AssignmentSubmissionResponse)
async def grade_submission(
    submission_id: str,
    grade_data: GradeSubmission,
    current_user: dict = Depends(get_current_user)
):
    """Grade a submission (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can grade submissions"
        )

    submission = await get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    graded_submission = await grade_submission_crud(
        submission_id, grade_data.grade, grade_data.feedback
    )
    return graded_submission


# -------------------- LATE SUBMISSION APPROVALS -------------------- #
@router.post("/{assignment_id}/approve-late", response_model=LateSubmissionApprovalResponse)
async def approve_late_submission(
    assignment_id: str,
    approval_data: LateSubmissionApprovalCreate,
    current_user: dict = Depends(get_current_user)
):
    """Approve late submission for a student (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can approve late submissions"
        )

    approval = await create_late_approval_crud(approval_data.dict())
    return approval


# -------------------- EXTENSION REQUESTS -------------------- #
@router.post("/{assignment_id}/request-extension", response_model=ExtensionRequestResponse)
async def request_extension(
    assignment_id: str,
    request_data: ExtensionRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Request extension for an assignment (Students only)"""
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can request extensions"
        )

    # Check assignment exists
    assignment = await get_assignment_by_id(assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )

    # Create extension request
    request_data_dict = request_data.dict()
    request_data_dict["user_id"] = current_user.id
    request_data_dict["assignment_id"] = assignment_id
    
    extension_request = await create_extension_request_crud(request_data_dict)
    return extension_request


@router.get("/{assignment_id}/extension-requests", response_model=List[ExtensionRequestResponse])
async def get_extension_requests(
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get extension requests for an assignment (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can view extension requests"
        )

    requests = await get_extension_requests_by_assignment(assignment_id)
    return requests


@router.put("/extension-requests/{request_id}", response_model=ExtensionRequestResponse)
async def update_extension_request(
    request_id: str,
    update_data: ExtensionRequestUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject an extension request (Admin/Instructor only)"""
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and instructors can update extension requests"
        )

    updated_request = await update_extension_request_crud(request_id, update_data.status)
    return updated_request


@router.get("/{course_id}/{assignment_id}/my-submission", response_model=Optional[AssignmentSubmissionResponse])
async def get_my_submission(
    course_id: str,  # Add this
    assignment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get current user's submission for an assignment"""
    submission = await get_submission_by_user_and_assignment(current_user.id, assignment_id)
    return submission


async def get_enrolled_courses(user_id: str) -> List[str]:
    """Get list of course IDs that the user is enrolled in - FIXED VERSION"""
    try:
        db = await get_database()
        
        # FIXED: Convert user_id to ObjectId for query
        enrollments = await db.enrollments.find({
            "user_id": ObjectId(user_id)  # FIXED: Convert to ObjectId
        }).to_list(length=100)
        
        enrolled_course_ids = []
        for enrollment in enrollments:
            # Convert the enrolled course_id to string
            enrolled_course_id = str(enrollment["course_id"])
            enrolled_course_ids.append(enrolled_course_id)
        
        print(f"🔍 DEBUG: User {user_id} enrolled in {len(enrolled_course_ids)} courses: {enrolled_course_ids}")
        return enrolled_course_ids
        
    except Exception as e:
        print(f"❌ Error in get_enrolled_courses: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return []