# Kiến trúc hệ thống

Cập nhật: `2026-05-08`.

Tài liệu này chỉ mô tả kiến trúc và các quyết định thiết kế chính. Chi tiết API nằm ở `docs/api-contract.md`; chi tiết database/env nằm ở `docs/database-setup.md`.

## Mục tiêu triển khai

Mục tiêu cuối cùng:

```powershell
docker compose up -d --build
```

Stack cuối cần có:

- `mysql`
- `redis`
- `minio`
- `qdrant`
- `backend`
- `worker`
- `frontend` (image bao gồm Nginx phục vụ SPA tĩnh + reverse proxy `/api` tới `backend`)

Hiện tại đã chạy được bằng Docker:

- `mysql`
- `redis`
- `minio`
- `qdrant`
- `backend`
- `worker`

Chưa xong:

- `frontend`

## Thành phần

| Thành phần | Vai trò |
| --- | --- |
| `backend` | FastAPI monolith cho auth, employee, enrollment, attendance |
| `worker` | RQ worker xử lý enrollment background jobs |
| `mysql` | Source of truth cho dữ liệu nghiệp vụ |
| `redis` | Queue cho RQ |
| `minio` | Lưu ảnh enrollment và snapshot nếu cần |
| `qdrant` | Lưu/search face embedding |
| `frontend` | Image multi-stage: build SPA bằng Vite, runtime dùng Nginx phục vụ static + reverse proxy `/api` → `backend` |

## Cấu trúc repo

Cấu trúc repo nên phản ánh đúng kiến trúc: backend monolith, worker nền, AI logic dùng chung, tài liệu và script tách riêng.

```text
backend/
  app/
    api/
      routes/             API endpoints
      deps.py             dependency chung như auth/db
      router.py           gom router chính
    db/                   session và SQLAlchemy base
    models/               ORM models: users, employees, enrollments, attendance
    schemas/              Pydantic request/response schemas
    services/             business logic và integration logic
    config.py             đọc env và settings
    main.py               FastAPI app entrypoint
    security.py           JWT/password helpers
  alembic/                database migrations
  Dockerfile              image cho backend
  docker_entrypoint.py    wait DB, migration, seed, start API

worker/
  app/
    jobs.py               xử lý enrollment jobs
    run_worker.py         RQ worker entrypoint
  Dockerfile              image cho worker

recognition/
  pipelines/              PoC detect/embed/evaluation

scripts/
  poc/                    lệnh chạy PoC local
  seed/                   seed admin/demo data

tests/
  backend/                unit tests cho backend service/route/worker

docs/                     tài liệu kỹ thuật
requirements/             dependency theo vai trò
docker-compose.yml        stack local/Docker Compose
```

## Quyết định thiết kế

- Backend là FastAPI monolith, không tách microservice trong MVP.
- Enrollment chạy async qua Redis/RQ vì upload và tạo embedding có thể chậm.
- Attendance chạy sync trong backend vì kiosk cần phản hồi nhanh.
- MySQL là nguồn dữ liệu nghiệp vụ chính.
- MinIO chỉ lưu object; Qdrant chỉ lưu vector index.
- Logic detect/extract embedding dùng chung qua `backend/app/services/face_analyzer.py`.
- MVP ưu tiên CPU-first, single-node, dễ demo bằng Docker Compose.

## Luồng enrollment

1. Admin tạo employee.
2. Admin upload 1-5 ảnh enrollment.
3. Backend lưu ảnh vào MinIO.
4. Backend tạo enrollment records trong MySQL.
5. Backend enqueue job vào Redis/RQ.
6. Worker tải ảnh từ MinIO.
7. Worker detect face và tạo embedding.
8. Worker upsert embedding vào Qdrant.
9. Worker cập nhật trạng thái enrollment trong MySQL.

Quy tắc MVP:

- Một ảnh enrollment hợp lệ khi detect đúng 1 khuôn mặt và upsert Qdrant thành công.
- Enrollment `success` khi có ít nhất 1 ảnh xử lý thành công.
- Enrollment `failed` khi tất cả ảnh thất bại.

## Luồng attendance

1. Kiosk gửi frame lên `POST /api/attendance/frame`.
2. Backend detect face và tạo embedding.
3. Backend search nearest vector trong Qdrant.
4. Backend so sánh score với `ATTENDANCE_THRESHOLD`.
5. Backend ghi `attendance_events`.
6. Backend trả kết quả cho kiosk.

Status MVP:

- `recorded`: nhận diện được nhân viên.
- `unknown_face`: không nhận diện được hoặc score dưới threshold.
- `multiple_faces`: frame có nhiều hơn 1 khuôn mặt.

## Dữ liệu chính

MySQL tables:

- `users`
- `employees`
- `enrollments`
- `enrollment_images`
- `attendance_events`

Qdrant collection:

- `employee_faces`

MinIO buckets:

- `enrollments`
- `snapshots`

## Trạng thái hiện tại

Đã hoàn thành:

- Auth admin.
- Employee CRUD.
- Enrollment API.
- Worker enrollment.
- Qdrant/MinIO integration.
- Attendance recognition.
- Attendance history.
- Backend unit tests.
- Backend Docker Compose stack.

Chưa hoàn thành:

- Frontend admin.
- Frontend kiosk.
- Frontend image (Vite build + Nginx serve + proxy `/api`).
- Full-stack Compose.

## Mốc tiếp theo

1. Làm frontend admin: login, employee CRUD, upload enrollment, xem job status.
2. Làm frontend kiosk: camera/frame upload, check-in/check-out, hiển thị kết quả.
3. Đóng gói frontend bằng image multi-stage (Vite build → Nginx serve + reverse proxy `/api`) và thêm service `frontend` vào `docker-compose.yml`.
4. Chạy full stack bằng `docker compose up -d --build`.

Thiết kế chi tiết frontend: xem `docs/frontend-design.md`.

## Definition of Done cho MVP

- Admin login được.
- CRUD nhân viên được.
- Upload enrollment được.
- Worker index embedding vào Qdrant được.
- Attendance nhận diện được nhân viên đã enroll.
- Attendance từ chối được người lạ.
- History xem được event mới.
- Toàn bộ hệ thống chạy bằng `docker compose up -d --build`.
