# Phạm vi dự án

Cập nhật: `2026-05-09`.

## Use case

Check-in/check-out nhân viên bằng nhận diện khuôn mặt.

Phạm vi MVP:

- 1 điểm chấm công.
- 1 luồng frontend người dùng: Kiosk UI.
- 1 luồng frontend quản trị: Admin UI.
- Nhân viên nội bộ.
- Docker Compose single-node.

## Ánh xạ với đề bài

| Yêu cầu | Cách project đáp ứng |
| --- | --- |
| Frontend người dùng | Kiosk UI mở camera, gửi frame và hiển thị kết quả chấm công |
| Frontend quản trị | Admin UI quản lý nhân viên, enrollment, lịch sử, cấu hình read-only |
| Backend | FastAPI |
| Database | MySQL |
| Object storage | MinIO |
| Vector database | Qdrant |
| Message/event queue | Redis + RQ |
| Nginx/load balancer | Nginx trong frontend container |

## In scope

- Admin login.
- Employee CRUD.
- Upload ảnh enrollment.
- Worker tạo embedding.
- Qdrant search embedding.
- Kiosk gửi frame check-in/check-out.
- Lưu attendance history.
- Trang admin cấu hình hệ thống read-only.
- Đóng gói bằng Docker Compose và image Docker Hub.

## Out of scope

- Employee self-service portal.
- Multi-camera.
- Mobile app.
- Tính công, bảng lương, ca kíp.
- Anti-spoofing/liveness.
- Role matrix phức tạp.
- Dashboard analytics nặng.
- Kubernetes.
- Train model riêng bằng dataset lớn.

## Trạng thái hiện tại

Đã xong:

- Backend core.
- Enrollment pipeline.
- Worker pipeline.
- Attendance API.
- Attendance history.
- Backend tests.
- Frontend admin.
- Frontend kiosk.
- Frontend image (Nginx serve + proxy `/api`).
- Full-stack Compose.
- Demo guide.
- AI tuning cơ bản cho demo: threshold, lọc false-positive nhỏ, warm-up model.
- Trang cấu hình hệ thống read-only.
- Compose chính dùng image Docker Hub; compose build override dùng cho developer.
- 3 image Docker Hub đã được build/push với namespace `tlam281206`.

Cần kiểm tra cuối:

- Dry-run demo đầy đủ qua `http://localhost:8080`.
- Chuẩn bị bộ ảnh enrollment đủ rõ và đa góc cho người demo chính.
- Chỉnh `ATTENDANCE_THRESHOLD` trong `.env.docker` nếu dữ liệu demo thực tế cần.

## Tiêu chí MVP cuối

- Admin login được.
- Tạo/sửa/xóa nhân viên được.
- Upload enrollment được.
- Worker ghi embedding vào Qdrant được.
- Kiosk nhận diện được nhân viên đã enroll.
- Kiosk từ chối được người lạ.
- Kiosk báo được trường hợp nhiều khuôn mặt.
- History có event mới.
- Admin xem được cấu hình hệ thống read-only.
- `docker compose up -d` chạy được full stack bằng image Docker Hub.

## Thứ tự làm tiếp

1. Chạy lại bản nộp bằng `docker compose pull` và `docker compose up -d`.
2. Test dry-run đầy đủ: admin, employee CRUD, enrollment, kiosk, history.
3. Chuẩn bị dữ liệu demo ổn định: 3-5 ảnh enrollment rõ mặt cho mỗi người.
4. Commit source code của mốc này.
5. Nộp repo, Docker Hub images và hướng dẫn demo.
