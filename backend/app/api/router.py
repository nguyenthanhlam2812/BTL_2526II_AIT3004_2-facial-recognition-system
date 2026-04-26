from fastapi import APIRouter

from backend.app.api.routes.attendance import router as attendance_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.employees import router as employees_router
from backend.app.api.routes.enrollments import router as enrollments_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(employees_router)
api_router.include_router(enrollments_router)
api_router.include_router(attendance_router)
