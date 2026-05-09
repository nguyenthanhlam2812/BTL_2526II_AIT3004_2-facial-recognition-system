# Phạm vi dự án

Cập nhật: `2026-05-09`.

## Use case

Check-in/check-out nhân viên bằng nhận diện khuôn mặt.

Phạm vi MVP:

- 1 điểm chấm công.
- 1 luồng admin.
- 1 luồng kiosk.
- Nhân viên nội bộ.
- Docker Compose single-node.

## In scope

- Admin login.
- Employee CRUD.
- Upload ảnh enrollment.
- Worker tạo embedding.
- Qdrant search embedding.
- Kiosk gửi frame check-in/check-out.
- Lưu attendance history.
- Đóng gói bằng Docker Compose.

## Out of scope

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
- Backend Docker stack.
- Frontend admin.
- Frontend kiosk.
- Frontend image (Nginx serve + proxy `/api`).
- Full-stack Compose.
- Demo guide.
- AI tuning cơ bản cho demo: threshold, lọc false-positive nhỏ, warm-up model.

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
- History có event mới.
- `docker compose up -d --build` chạy được full stack.

## Thứ tự làm tiếp

1. Chạy dry-run demo đầy đủ bằng `docker compose up -d --build`.
2. Test admin: login, employee CRUD, enrollment, attendance history.
3. Test kiosk: camera, check-in/check-out, người lạ, nhiều khuôn mặt.
4. Chuẩn bị dữ liệu demo ổn định: 3-5 ảnh enrollment rõ mặt cho mỗi người.
5. Push/nộp MVP sau khi dry-run không còn lỗi blocker.
