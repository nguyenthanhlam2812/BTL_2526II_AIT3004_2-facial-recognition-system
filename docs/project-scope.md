# Phạm vi dự án

Cập nhật: `2026-05-08`.

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

Chưa xong:

- Frontend admin.
- Frontend kiosk.
- Frontend image (Nginx serve + proxy `/api`).
- Full-stack Compose.

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

1. Frontend admin.
2. Frontend kiosk.
3. Frontend image (Vite build + Nginx serve + proxy `/api`).
4. Full-stack Docker test.
5. Demo guide cuối.
