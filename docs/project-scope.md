# Phạm vi Dự án

## Tóm tắt scope

- Use case duy nhất: check-in/check-out nhân viên bằng nhận diện khuôn mặt.
- Phạm vi MVP: 1 camera, 1 điểm chấm công, 1 nhóm đối tượng là nhân viên nội bộ.
- Hệ thống gồm `/admin`, `/kiosk`, backend FastAPI, MySQL, MinIO, Qdrant, Redis + RQ, nginx và Docker Compose.

## In scope

- Admin CRUD nhân viên.
- Admin upload ảnh đăng ký khuôn mặt.
- Worker tạo embedding nền.
- Kiosk nhận frame và trả kết quả check-in/check-out.
- Lưu attendance history.
- Đóng gói toàn hệ thống bằng Docker Compose.

## Out of scope for MVP

- Multi-camera.
- Mobile app.
- Tính công, bảng lương, ca kíp và báo cáo HR phức tạp.
- Anti-spoofing hoặc liveness.
- Role matrix phức tạp.
- Dashboard analytics nặng.
- Kubernetes hoặc monitoring stack phức tạp.

## Tiêu chí thành công

- Demo nhận diện được ít nhất 1 nhân viên đã enroll và ghi được check-in/check-out.
- Từ chối được ít nhất 1 người lạ.
- History lưu được attendance event mới sau khi nhận diện.
- Admin tạo được nhân viên và upload được ảnh đăng ký.
- Worker tạo được embedding và Qdrant có dữ liệu.
- `docker compose up -d` chạy được full stack.
- README đủ để chạy lại hệ thống trên máy khác.

## Điều kiện chấp nhận MVP

- Luồng enroll -> embedding -> recognize -> attendance log chạy được end-to-end.
- Không phát sinh tính năng ngoài scope làm chậm tiến độ.
- Hệ thống bám đúng thành phần bắt buộc trong brief môn học.
