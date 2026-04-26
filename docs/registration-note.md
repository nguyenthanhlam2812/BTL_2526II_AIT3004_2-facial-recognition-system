# Ghi chú Đăng ký Đề tài

## Tên đề tài đề xuất

Hệ thống check-in/check-out nhân viên bằng nhận diện khuôn mặt thời gian thực

## Bài toán

Công ty cần một hệ thống ghi nhận check-in/check-out của nhân viên bằng camera tại điểm chấm công. Giải pháp cần nhận diện nhanh, lưu lịch sử sự kiện rõ ràng, và có thể demo ổn định trên môi trường Docker.

## Mục tiêu

- Xây dựng MVP check-in/check-out bằng nhận diện khuôn mặt cho 1 điểm chấm công.
- Hỗ trợ đăng ký nhân viên bằng ảnh khuôn mặt.
- Thực hiện recognition và ghi attendance event `check_in` hoặc `check_out`.
- Lưu history và snapshot cho mỗi sự kiện cần thiết.

## Phạm vi thực hiện

- 1 camera.
- 1 điểm chấm công.
- 1 nhóm đối tượng: nhân viên nội bộ.
- 1 frontend với `/admin` và `/kiosk`.
- 1 backend FastAPI + 1 worker.
- MySQL + Qdrant + MinIO + Redis/RQ + Docker Compose.
- nginx điều phối request giữa frontend và backend.

## Công nghệ dự kiến

- React + Vite + TypeScript.
- FastAPI.
- InsightFace + OpenCV.
- MySQL.
- Qdrant.
- MinIO.
- Redis + RQ.
- Nginx.
- Docker Compose.

## Deliverable dự kiến

- Source code đầy đủ.
- `docker-compose.yml`.
- Docker images trên Docker Hub.
- README quickstart.
- Demo live end-to-end.
- Tài liệu kiến trúc và mô tả use case.

## Lý do đề tài khả thi

- Phạm vi được giới hạn rõ ràng trong 1 use case vision realtime.
- Stack phù hợp với AI system engineering và dễ đóng gói.
- Có thể chia việc rõ giữa AI, backend, frontend và integration.
- Không mở rộng sang payroll hoặc HR workflow phức tạp trong MVP.
