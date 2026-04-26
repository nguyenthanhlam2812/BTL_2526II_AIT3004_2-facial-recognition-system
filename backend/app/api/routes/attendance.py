from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/frame")
def recognize_attendance_frame() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Route scaffolded theo API contract, chưa triển khai attendance recognition.",
    )


@router.get("/events")
def list_attendance_events() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Route scaffolded theo API contract, chưa triển khai attendance history.",
    )
