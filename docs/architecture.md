# Kiến trúc hệ thống

Tài liệu này mô tả kiến trúc triển khai của bản nộp hiện tại. Chi tiết API nằm ở `docs/api-contract.md`; chi tiết database/env nằm ở `docs/database-setup.md`.

## Mục tiêu triển khai

Bản nộp dùng Docker Compose và image đã push lên Docker Hub. Giảng viên có thể chạy:

```powershell
docker compose pull
docker compose up -d
```

Khi developer cần build local:

```powershell
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build backend worker frontend
```

## Thành phần runtime

| Thành phần | Vai trò |
| --- | --- |
| `frontend` | React/Vite SPA phục vụ bằng Nginx; gồm Admin UI và Kiosk UI; proxy `/api` tới backend |
| `backend` | FastAPI monolith cho auth, employee, enrollment, attendance, reports, admin users và system settings |
| `worker` | RQ worker xử lý enrollment background jobs |
| `mysql` | Nguồn dữ liệu chính cho dữ liệu nghiệp vụ |
| `redis` | Queue cho RQ |
| `minio` | Object storage cho ảnh enrollment và snapshot |
| `qdrant` | Vector database lưu/search face embedding |

Frontend người dùng trong đề bài là `Kiosk UI`: mở camera, gửi frame và hiển thị kết quả chấm công. Frontend quản trị là `Admin UI`: đăng nhập, dashboard tổng quan, quản lý người dùng quản trị, nhân viên, enrollment, lịch sử, báo cáo và cấu hình hệ thống.

## Cấu trúc repo

```text
backend/
  app/
    api/
      routes/             API endpoints (auth, employees, enrollments, attendance/reports, admin users, system)
      deps.py             dependency chung như auth/db
      router.py           gom router chính
    db/                   session và SQLAlchemy base
    models/               ORM models: users, employees, enrollments, attendance, system settings
    schemas/              Pydantic request/response schemas cho auth, users, employees, attendance, system
    services/             business logic và integration logic
    config.py             đọc env và settings
    main.py               FastAPI app entrypoint
    rate_limit.py         cấu hình limiter cho kiosk endpoint
    security.py           JWT/password helpers
  alembic/                database migrations
  Dockerfile
  docker_entrypoint.py    wait DB, migration, seed, start API

worker/
  app/
    jobs.py               xử lý enrollment jobs
    run_worker.py         RQ worker entrypoint
  Dockerfile

frontend/
  public/
    vendor/mediapipe/models/
                         model face detector dùng local runtime
  scripts/
    prepare-mediapipe-assets.mjs
                         copy WASM assets từ node_modules trước build/dev
  src/
    routes/
      admin/              Admin UI (Dashboard, Employees, Enroll, Attendance, Reports, Users, System)
      kiosk/              Kiosk UI, detector hook, overlay và scan components
    shared/
      api/                Axios wrappers (auth, employees, attendance, enrollments, kiosk, system)
      hooks/              useAuth, useRequireAuth
      lib/                access control và token helpers
      types/              TypeScript interfaces cho API
      ui/                 Shared UI components (StatCard, GlowDot, PageHeader, AccessDeniedState)
    styles/               globals.css: CSS custom properties, glow utilities, scan animation
    main.tsx              MantineProvider với dark theme (forceColorScheme="dark")
    App.tsx               React Router routes
  Dockerfile              build SPA và serve bằng Nginx
  nginx.conf.template     reverse proxy `/api` tới backend và inject kiosk token server-side

recognition/
  pipelines/              PoC detect/embed/evaluation

scripts/
  poc/                    lệnh chạy PoC local
  seed/                   seed admin/demo data

tests/
  backend/                unit tests cho route/service/worker và quyền truy cập

docs/                     tài liệu kỹ thuật
requirements/             dependency theo vai trò
docker-compose.yml        stack dùng image Docker Hub
docker-compose.build.yml  build image từ mã nguồn local
docker-compose.tunnel.yml mở public demo qua Cloudflare Tunnel
```

## Quyết định thiết kế

- Backend là FastAPI monolith để giữ hệ thống gọn, dễ demo và dễ deploy.
- Enrollment chạy async qua Redis/RQ vì upload và tạo embedding có thể chậm.
- Attendance chạy sync trong backend vì kiosk cần phản hồi ngay.
- Reports và dashboard summary chạy từ backend aggregate để frontend không phải tự suy từ event list.
- MySQL lưu dữ liệu nghiệp vụ chính.
- MinIO lưu object ảnh; Qdrant lưu vector embedding.
- Logic detect/extract embedding dùng chung qua `backend/app/services/face_analyzer.py`.
- Nginx nằm trong image `frontend`, không tách service `nginx` riêng trong MVP.
- Kiosk detector dùng MediaPipe assets local qua script prepare step, không phụ thuộc CDN runtime.
- System settings endpoint chỉ trả cấu hình không nhạy cảm; owner có thể sửa các runtime settings an toàn, còn admin/viewer chỉ xem.
- Frontend dùng Mantine v9 với `forceColorScheme="dark"` và custom theme; toàn bộ app chạy dark mode mặc định, không có toggle.

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

Trạng thái chấm công:

- `recorded`: nhận diện được nhân viên.
- `unknown_face`: không nhận diện được hoặc score dưới threshold.
- `multiple_faces`: frame có nhiều hơn 1 khuôn mặt hợp lệ.

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

## Image Docker Hub

```text
tlam281206/ai-facial-recognition-backend:latest
tlam281206/ai-facial-recognition-worker:latest
tlam281206/ai-facial-recognition-frontend:latest
```

`docker-compose.yml` dùng các image này. `docker-compose.build.yml` chỉ dùng khi developer cần build lại image từ mã nguồn local.

## Tiêu chí hoàn thành cho bản nộp

- Admin login được.
- CRUD nhân viên được.
- Upload enrollment được.
- Worker index embedding vào Qdrant được.
- Kiosk nhận diện được nhân viên đã enroll.
- Kiosk từ chối được người lạ.
- Kiosk báo được trường hợp nhiều khuôn mặt.
- Dashboard hiển thị stat cards và biểu đồ chính xác.
- History xem được event mới.
- Owner sửa được cấu hình runtime an toàn; admin/viewer xem ở chế độ read-only.
- Toàn bộ hệ thống chạy bằng Docker Compose.
