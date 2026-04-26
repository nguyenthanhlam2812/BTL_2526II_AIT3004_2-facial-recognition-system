from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("")
def list_employees() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Route scaffolded theo API contract, chưa triển khai danh sách nhân viên.",
    )


@router.post("")
def create_employee() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Route scaffolded theo API contract, chưa triển khai tạo nhân viên.",
    )


@router.put("/{employee_id}")
def update_employee(employee_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Route scaffolded theo API contract, chưa triển khai cập nhật nhân viên {employee_id}.",
    )


@router.delete("/{employee_id}")
def delete_employee(employee_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Route scaffolded theo API contract, chưa triển khai xoá nhân viên {employee_id}.",
    )
