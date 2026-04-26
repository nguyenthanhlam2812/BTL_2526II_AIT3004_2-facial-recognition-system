from fastapi import APIRouter, HTTPException, status


router = APIRouter(tags=["enrollments"])


@router.post("/employees/{employee_id}/enrollments")
def create_enrollment(employee_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Route scaffolded theo API contract, chưa triển khai enrollment cho nhân viên {employee_id}.",
    )


@router.get("/enrollments/{job_id}")
def get_enrollment_status(job_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Route scaffolded theo API contract, chưa triển khai trạng thái job {job_id}.",
    )
