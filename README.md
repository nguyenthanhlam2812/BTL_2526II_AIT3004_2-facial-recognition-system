# AI Facial Recognition Attendance

MVP chấm công nhân viên bằng nhận diện khuôn mặt.

Mục tiêu bàn giao cuối cùng:

```powershell
docker compose up -d --build
```

## Trạng thái hiện tại

Cập nhật: `2026-05-08`.

Đã xong:

- Backend FastAPI: healthcheck, auth JWT, employee CRUD.
- Enrollment: upload ảnh, lưu MinIO, enqueue Redis/RQ.
- Worker: xử lý ảnh enrollment, tạo embedding, upsert Qdrant, cập nhật MySQL.
- Attendance: nhận frame, nhận diện, ghi event, xem history.
- Backend tests: `17 passed`.
- Docker backend stack: `mysql`, `redis`, `minio`, `qdrant`, `backend`, `worker`.

Chưa xong:

- Frontend admin.
- Frontend kiosk.
- Frontend image (Vite build + Nginx serve + proxy `/api`).
- Demo guide cuối cho giảng viên.

## Cấu trúc chính

```text
backend/          FastAPI app
worker/           RQ worker xử lý enrollment
recognition/      PoC và logic AI dùng chung
scripts/          PoC scripts và seed admin
tests/            Backend tests
docs/             Tài liệu kỹ thuật
requirements/     Dependency theo vai trò
docker-compose.yml
```

## Chạy backend stack bằng Docker

```powershell
docker compose build backend worker
docker compose up -d mysql redis minio qdrant backend worker
docker compose ps
```

Kiểm tra logs:

```powershell
docker compose logs backend --tail=150
docker compose logs worker --tail=120
```

Backend đúng sẽ có:

```text
Database is ready.
Running: /usr/local/bin/python -m alembic upgrade head
Running: /usr/local/bin/python scripts/seed/seed_admin.py
Uvicorn running on http://0.0.0.0:8000
```

Worker đúng sẽ có:

```text
Listening on enrollment...
```

Swagger:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Chạy backend local

Tạo env:

```powershell
Copy-Item .env.example .env
```

Nếu MySQL local chạy port `3307`, giữ `MYSQL_PORT=3307` trong `.env`. Docker MySQL vẫn dùng port `3306` qua `.env.docker.example`.

Cài dependency:

```powershell
.\.venv\Scripts\pip install -r requirements\backend.txt
.\.venv\Scripts\pip install -r requirements\dev.txt
```

Chạy dependency nền nếu cần:

```powershell
docker compose up -d redis minio qdrant
```

Chạy migration và seed:

```powershell
.\.venv\Scripts\alembic upgrade head
.\.venv\Scripts\python scripts\seed\seed_admin.py
```

Chạy API:

```powershell
.\.venv\Scripts\python -m uvicorn backend.app.main:app --reload
```

Chạy worker:

```powershell
.\.venv\Scripts\python -m worker.app.run_worker
```

Tài khoản admin mặc định:

- `admin`
- `admin123`

## Chạy test

```powershell
.\.venv\Scripts\python -m pytest tests\backend -q
```

## API hiện có

- `POST /api/auth/login`
- `GET /api/employees`
- `POST /api/employees`
- `PUT /api/employees/{employee_id}`
- `DELETE /api/employees/{employee_id}`
- `POST /api/employees/{employee_id}/enrollments`
- `GET /api/enrollments/{job_id}`
- `POST /api/attendance/frame`
- `GET /api/attendance/events`
- `GET /healthz`

## Tài liệu

- `docs/project-scope.md`: phạm vi và tiêu chí MVP.
- `docs/architecture.md`: kiến trúc hệ thống.
- `docs/api-contract.md`: contract API cho frontend.
- `docs/frontend-design.md`: thiết kế frontend (stack, cấu trúc, lộ trình).
- `docs/learning-notes.md`: ghi chú học tập và cách dùng AI hỗ trợ.
- `docs/database-setup.md`: local DB và Docker DB.
- `docs/demo-data.md`: dữ liệu demo và consent.
- `docs/diagrams.md`: sơ đồ Mermaid và ERD.

## Kế hoạch tiếp theo

1. Commit mốc docs/backend compose-ready.
2. Làm frontend admin.
3. Làm frontend kiosk.
4. Đóng gói frontend (Vite build + Nginx serve + proxy `/api`) và thêm vào Compose.
5. Chạy mục tiêu cuối: `docker compose up -d --build`.
