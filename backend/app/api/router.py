from fastapi import APIRouter

from backend.app.api.routes.admin_users import router as admin_users_router
from backend.app.api.routes.audit_logs import router as audit_logs_router
from backend.app.api.routes.attendance import router as attendance_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.employees import router as employees_router
from backend.app.api.routes.enrollments import router as enrollments_router
from backend.app.api.routes.system import router as system_router


api_router = APIRouter()
api_router.include_router(admin_users_router)
api_router.include_router(audit_logs_router)
api_router.include_router(auth_router)
api_router.include_router(employees_router)
api_router.include_router(enrollments_router)
api_router.include_router(attendance_router)
api_router.include_router(system_router)
