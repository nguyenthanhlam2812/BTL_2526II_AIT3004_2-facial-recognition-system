from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Route scaffolded theo API contract, chưa triển khai logic đăng nhập.",
    )
