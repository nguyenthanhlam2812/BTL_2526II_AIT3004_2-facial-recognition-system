from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_admin, require_operator
from backend.app.api.validators import ensure_image_mime, ensure_image_size_bytes
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.enrollment import (
    EnrollmentCreateResponse,
    EnrollmentStatusResponse,
)
from backend.app.services.enrollment_service import (
    DuplicateFaceEnrollmentError,
    EmployeeNotFoundError,
    EnrollmentInfrastructureError,
    InvalidEnrollmentFilesError,
    create_enrollment as create_enrollment_service,
    get_enrollment_by_job_id,
)
from backend.app.services.audit_log_service import record_audit_log

router = APIRouter(tags=["enrollments"])


@router.post(
    "/employees/{employee_id}/enrollments",
    response_model=EnrollmentCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment(
    employee_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> EnrollmentCreateResponse:
    for upload in files:
        ensure_image_mime(upload.content_type)
        if upload.size is not None:
            ensure_image_size_bytes(upload.size)

    try:
        enrollment = create_enrollment_service(db, employee_id, files)
    except EmployeeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        ) from exc
    except InvalidEnrollmentFilesError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DuplicateFaceEnrollmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except EnrollmentInfrastructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    record_audit_log(
        db,
        actor=current_user,
        action="enrollment.submit",
        resource_type="enrollment",
        resource_id=enrollment.id,
        resource_label=enrollment.job_id,
        metadata={
            "job_id": enrollment.job_id,
            "employee_id": enrollment.employee_id,
            "uploaded_count": enrollment.uploaded_count,
        },
    )
    return enrollment


@router.get(
    "/enrollments/{job_id}",
    response_model=EnrollmentStatusResponse,
)
def get_enrollment_status(
    job_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> EnrollmentStatusResponse:
    enrollment = get_enrollment_by_job_id(db, job_id)
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment job not found.",
        )

    return enrollment
