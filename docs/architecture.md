# Kiến trúc hệ thống

Tài liệu này mô tả kiến trúc của bản nộp AI Facial Recognition Attendance: một hệ thống chấm công nội bộ bằng nhận diện khuôn mặt, chạy bằng Docker Compose và có đủ frontend người dùng, frontend quản trị, backend, queue, database, object storage, vector database và Nginx.

## Mục tiêu nghiệp vụ

Hệ thống phục vụ mô hình một công ty có điểm chấm công chung:

- Nhân viên đi qua kiosk đặt tại văn phòng để check-in/check-out.
- Quản trị viên vận hành danh mục, hồ sơ nhân viên, enrollment khuôn mặt, lịch sử chấm công và báo cáo.
- Chủ hệ thống quản lý tài khoản quản trị, cấu hình runtime và audit log.

Kiosk không phải là cổng cá nhân của từng nhân viên. Nhân viên không cần đăng nhập để chấm công; backend nhận diện người trong frame và quyết định ghi nhận hay từ chối.

## Thành phần runtime

| Thành phần | Vai trò |
| --- | --- |
| `nginx` | Reverse proxy đứng trước app, route `/*` tới frontend, `/api/*` tới backend, inject `X-Kiosk-Token` cho `/api/attendance/frame` |
| `frontend` | React/Vite/Mantine SPA, gồm Admin UI và Kiosk UI |
| `backend` | FastAPI xử lý auth, users, employees, lookups, enrollments, attendance, reports, audit logs, system settings |
| `worker` | RQ worker xử lý ảnh enrollment nền |
| `mysql` | Nguồn dữ liệu nghiệp vụ chính |
| `redis` | Queue enrollment và duplicate gate cho kiosk |
| `minio` | Lưu ảnh enrollment |
| `qdrant` | Lưu/search embedding khuôn mặt |

Image Docker Hub:

```text
tlam281206/ai-facial-recognition-backend:latest
tlam281206/ai-facial-recognition-worker:latest
tlam281206/ai-facial-recognition-frontend:latest
tlam281206/ai-facial-recognition-nginx:latest
```

Admin UI và Kiosk UI chạy trong cùng `frontend` image nhưng là hai surface riêng: `/login` và `/admin/*` cho quản trị, `/kiosk` cho điểm chấm công dùng chung.

## Cấu trúc repo

```text
backend/        FastAPI app, SQLAlchemy models, Alembic migrations, services
worker/         RQ worker cho enrollment
frontend/       React admin/kiosk UI
nginx/          Reverse proxy image
recognition/    PoC nhận diện và đánh giá threshold
scripts/        Seed/demo helper scripts
tests/          Backend + frontend tests
docs/           Tài liệu nộp bài
requirements/   Dependency theo backend/worker/test/dev
```

## Data flow chính

### Đăng ký khuôn mặt

1. Admin tạo nhân viên và chọn phòng ban/chức vụ từ danh mục.
2. Admin upload ảnh hoặc dùng camera mode chụp 3 góc `front`, `left`, `right`.
3. Backend lưu ảnh vào MinIO, tạo bản ghi enrollment trong MySQL.
4. Backend đẩy job vào Redis.
5. Worker đọc ảnh, detect face, tạo embedding.
6. Worker ghi vector vào Qdrant và cập nhật trạng thái enrollment trong MySQL.

Enrollment `success` khi có ít nhất một ảnh xử lý thành công. Nếu toàn bộ ảnh lỗi, enrollment `failed`.

### Chấm công

1. Kiosk gửi frame tới `POST /api/attendance/frame`.
2. Nginx inject `X-Kiosk-Token`; gọi trực tiếp backend không có token sẽ bị 401.
3. Backend detect face, tạo embedding và search Qdrant.
4. Backend so sánh score với threshold runtime.
5. Nếu match employee active, backend ghi event `recorded`.
6. Nếu không match hoặc nhiều mặt, backend ghi `unknown_face` hoặc `multiple_faces` theo cấu hình `record_unmatched`.
7. Redis camera gate chặn ghi trùng cùng nhân viên trong cửa sổ 5 phút.

Trạng thái attendance:

- `recorded`: nhận diện và ghi nhận thành công.
- `unknown_face`: không có match đủ ngưỡng hoặc không có mặt hợp lệ.
- `multiple_faces`: frame có nhiều khuôn mặt hợp lệ.

### Báo cáo

Dashboard và báo cáo ngày dùng aggregate từ backend, không để frontend tự suy từ danh sách event. Múi giờ nghiệp vụ mặc định là `Asia/Ho_Chi_Minh`; đi muộn khi check-in đầu tiên sau 09:00.

## Dữ liệu chính

MySQL tables:

- `users`: tài khoản admin console.
- `employees`: hồ sơ nhân viên.
- `departments`, `positions`: danh mục dùng khi tạo/sửa nhân viên.
- `enrollments`, `enrollment_images`: job enrollment và ảnh nguồn.
- `attendance_events`: event check-in/check-out và event lỗi nhận diện.
- `audit_logs`: truy vết thao tác quản trị.
- `system_settings`: cấu hình runtime editable.

Qdrant collection:

- `employee_faces`

MinIO buckets:

- `enrollments`
- `snapshots` reserved cho hướng mở rộng; bản hiện tại chưa lưu snapshot chấm công dài hạn.

## Quyền và bảo mật

- `owner`: quản lý users, cấu hình, audit, toàn bộ nghiệp vụ.
- `admin`: vận hành danh mục, nhân viên, enrollment, chấm công, báo cáo.
- `viewer`: chỉ xem dashboard, nhân viên, chấm công, báo cáo.

Không có public signup. System settings và audit logs owner-only. User/password/employee input được validate ở backend; frontend chỉ hỗ trợ nhập đúng hơn chứ không phải lớp bảo vệ chính.

Public demo cần đổi `SEED_ADMIN_PASSWORD`, `JWT_SECRET_KEY`, `KIOSK_API_TOKEN`; backend fail-fast nếu bật `PUBLIC_DEMO_MODE=true` mà vẫn dùng secret mặc định.
Khi dùng Ngrok, `docker-compose.ngrok.yml` mở HTTPS public URL tới `nginx` và expose local inspector ở `http://localhost:4040`; `NGROK_AUTHTOKEN` chỉ đặt trong `.env.docker`, không commit.

## Phạm vi bản nộp

Trong phạm vi:

- Kiosk nhận diện khuôn mặt gần thời gian thực cho check-in/check-out: browser hiển thị camera live, frontend gate mặt cục bộ và backend nhận diện từng frame gửi lên.
- Admin console quản lý nhân viên, danh mục, enrollment, chấm công, báo cáo, users, settings, audit.
- Docker Compose chạy full stack bằng image Docker Hub.
- CI/CD build/test/push image và smoke-test đường chạy nộp bài.

Ngoài phạm vi:

- Employee self-service portal.
- Ca kíp phức tạp, nghỉ phép, overtime, payroll.
- Multi-site/multi-camera production.
- Production-grade anti-spoofing.
- Backup/restore tự động và monitoring chuyên sâu.
- Kubernetes/Helm.

## Hướng mở rộng

- Tích hợp model chống giả mạo khuôn mặt, camera depth hoặc challenge-response.
- Thêm module chính sách chấm công: ca làm, ngày lễ, nghỉ phép, tăng ca.
- Thêm backup định kỳ cho MySQL/MinIO/Qdrant.
- Thêm monitoring cho queue depth, job failure, latency nhận diện.
- Thêm offline queue cho kiosk khi mất mạng.
