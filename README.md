# AI Facial Recognition Attendance

MVP chấm công nhân viên bằng nhận diện khuôn mặt. Bản hiện tại hướng tới mục tiêu người chấm có thể chạy toàn bộ hệ thống bằng Docker Compose:

```powershell
docker compose up -d --build
```

## Chạy nhanh

Yêu cầu:

- Docker Desktop
- Git

Chạy full stack:

```powershell
docker compose up -d --build
```

Các URL chính:

- Frontend: [http://localhost:8080](http://localhost:8080)
- Admin: [http://localhost:8080/login](http://localhost:8080/login)
- Kiosk: [http://localhost:8080/kiosk](http://localhost:8080/kiosk)
- Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- MinIO console: [http://localhost:9001](http://localhost:9001)

Tài khoản admin mặc định:

```text
admin / admin123
```

## Kiểm tra nhanh

```powershell
docker compose ps
docker compose logs backend --tail=100
docker compose logs worker --tail=100
```

Healthcheck:

```powershell
Invoke-WebRequest http://localhost:8080/healthz
```

## Luồng demo chính

1. Đăng nhập admin.
2. Tạo nhân viên.
3. Upload ảnh enrollment cho nhân viên.
4. Đợi job enrollment hoàn thành.
5. Mở kiosk, cho phép camera, thực hiện check-in hoặc check-out.
6. Kiểm tra bản ghi ở trang lịch sử chấm công.

## Công nghệ chính

- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: React, Vite, TypeScript, Mantine
- AI: InsightFace
- Database: MySQL
- Queue: Redis, RQ
- Object storage: MinIO
- Vector search: Qdrant
- Runtime: Docker Compose, Nginx trong frontend container

## Cấu trúc repo

```text
backend/          FastAPI app
worker/           RQ worker xử lý enrollment
frontend/         React admin UI và kiosk UI
recognition/      Logic AI dùng chung
scripts/          Script seed và PoC
tests/            Backend tests
docs/             Tài liệu kỹ thuật
requirements/     Python dependencies theo vai trò
docker-compose.yml
```

## Test

Backend:

```powershell
.\.venv\Scripts\python -m pytest tests\backend -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

## Tài liệu

- `docs/project-scope.md`: phạm vi và tiêu chí MVP.
- `docs/architecture.md`: kiến trúc hệ thống.
- `docs/api-contract.md`: contract API.
- `docs/database-setup.md`: cấu hình database local và Docker.
- `docs/demo-data.md`: dữ liệu demo và lưu ý consent.
- `docs/diagrams.md`: sơ đồ hệ thống.
