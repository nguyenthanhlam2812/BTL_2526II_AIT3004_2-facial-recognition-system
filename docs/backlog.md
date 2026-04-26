# Backlog MoSCoW

Ghi chú: Đây là product backlog của hệ thống và các deliverable kỹ thuật bắt buộc của bài nộp.

## Must

- Frontend kiosk mở camera, gửi frame định kỳ và hiển thị kết quả `check_in` / `check_out` hoặc `unknown_face`.
- Frontend kiosk cho chọn `check_in` hoặc `check_out`.
- Frontend admin đăng nhập được.
- Frontend admin CRUD nhân viên.
- Frontend admin upload ảnh đăng ký khuôn mặt cho nhân viên.
- Frontend admin xem attendance history.
- Backend có API auth admin.
- Backend có API employee CRUD.
- Backend có API upload enrollment images.
- Backend có API recognition cho attendance frame.
- Backend có API lấy attendance history.
- MySQL lưu users, employees, enrollments, attendance events.
- MinIO lưu ảnh đăng ký và snapshot.
- Qdrant lưu face embeddings và hỗ trợ truy vấn top-k.
- Redis + RQ chạy job tạo embedding nền.
- nginx điều phối request giữa frontend, backend và attendance endpoint.
- Dockerfile cho frontend, backend, worker.
- `docker-compose.yml` chạy full stack bằng `docker compose up -d`.
- Docker images được build và push lên Docker Hub.
- Có `.env.example`.
- Có README mô tả kiến trúc, dependency, biến môi trường và cách chạy lại hệ thống.

## Should

- Trạng thái enrollment `pending`, `success`, `failed`.
- Admin xem được trạng thái job tạo embedding.
- Filter history theo tên, thời gian, action type.
- Threshold config để chỉnh nhanh khi demo.
- Chỉ lưu snapshot cho `unknown_face` hoặc `multiple_faces`, hoặc cho phép cấu hình.
- Healthcheck cho các service chính.
- Seed dữ liệu demo và tài khoản admin mẫu.

## Could

- Daily attendance summary đơn giản.
- Kiosk reconnect indicator.
- Manual upload frame fallback.
- GitHub Actions build/test/push image.
- Auto cleanup dữ liệu cũ.
- Export CSV attendance logs.

## Won't for MVP

- Multi-camera.
- Mobile app.
- Tính công theo ca, bảng lương hoặc workflow HR đầy đủ.
- Anti-spoofing hoặc liveness.
- Role matrix phức tạp.
- Dashboard BI nặng.
- Microservices nhiều repo.
- Kubernetes.
- WebRTC full stack.

## Thứ tự ưu tiên thực hiện

1. Backend core + storage + queue.
2. Enrollment flow.
3. Attendance recognition flow.
4. Frontend admin.
5. Frontend kiosk.
6. Docker Compose + Docker Hub.
7. README + test + release.
8. Bonus.
