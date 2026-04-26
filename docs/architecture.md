# Kiến trúc Đề xuất

## Decision summary

- Frontend: 1 ứng dụng React với 2 route `/admin` và `/kiosk`.
- Backend: 1 FastAPI monolith cho toàn bộ nghiệp vụ.
- Queue chính: Redis + RQ để đáp ứng yêu cầu queue của môn học.
- Storage: MySQL + MinIO + Qdrant.
- Reverse proxy: nginx.
- Đóng gói: Docker Compose, ưu tiên single-node để demo ổn định.

## Assumptions

- 1 camera.
- 1 điểm chấm công.
- 1 nhóm đối tượng: nhân viên nội bộ.
- Browser chụp 1 frame mỗi 700-1000 ms.
- Backend chỉ xử lý khuôn mặt lớn nhất trong frame.
- Demo theo hướng CPU-first, không tối ưu cho tải lớn.

## Stack chính

| Thành phần | Lựa chọn |
| --- | --- |
| Frontend | React + Vite + TypeScript |
| Backend | FastAPI |
| AI | InsightFace + OpenCV |
| Database | MySQL |
| Vector DB | Qdrant |
| Object storage | MinIO |
| Queue | Redis + RQ |
| Reverse proxy | nginx |
| Orchestration | Docker Compose |

## Ghi chú về queue

- Redis + RQ là phương án chính để nộp bài.
- `BackgroundTasks` chỉ là fallback tạm thời để debug hoặc cứu local dev khi worker có vấn đề.
- `BackgroundTasks` không phải phương án nộp chính.

## Service map

| Service | Trách nhiệm |
| --- | --- |
| `frontend` | UI cho `/admin` và `/kiosk` |
| `backend` | Auth, employee, enrollment, attendance, history |
| `worker` | Xử lý embedding jobs và cập nhật trạng thái |
| `mysql` | Lưu users, employees, enrollments, attendance events |
| `qdrant` | Lưu face embeddings và truy vấn top-k |
| `minio` | Lưu ảnh đăng ký và snapshot |
| `redis` | Queue cho worker |
| `nginx` | Điều phối request tới frontend và backend |

## Luồng chính

### Enrollment

1. Admin tạo employee.
2. Admin upload 3-5 ảnh khuôn mặt.
3. Backend lưu ảnh vào MinIO và tạo enrollment record trong MySQL.
4. Backend enqueue job vào Redis/RQ.
5. Worker đọc ảnh, detect face, extract embedding.
6. Worker upsert vector vào Qdrant và cập nhật trạng thái job.

### Attendance realtime

1. Kiosk mở webcam.
2. Frontend chọn `check_in` hoặc `check_out`, gửi frame JPEG định kỳ lên backend.
3. Backend detect face, lấy mặt lớn nhất.
4. Backend extract embedding, query Qdrant top-k, áp threshold.
5. Nếu match, backend ghi attendance event.
6. Backend trả `employee`, `score`, `action_type`, `attendance_status`.

## Threshold runtime

- Threshold phải là cấu hình, không hard-code chết trong code recognition.
- Giá trị PoC hiện tại là `0.26`, được suy ra từ bộ demo Phase 2.
- Giá trị này là mốc khởi đầu cho MVP, không phải threshold cuối cùng cho dữ liệu thật.

## Snapshot policy

- Mặc định chỉ lưu snapshot cho `unknown_face` hoặc các case lỗi cần debug.
- Có thể cho phép lưu theo config nếu cần phục vụ demo.

## Quy tắc xử lý MVP

- Không có mặt: `unknown_face`.
- Nhiều mặt: `multiple_faces`.
- Score dưới ngưỡng: `unknown_face`.
- Ưu tiên polling hoặc HTTP ổn định trước; WebSocket là tùy chọn nếu kịp.

## Out of scope for MVP

- Multi-camera.
- Tính công, payroll hoặc workflow HR phức tạp.
- Anti-spoofing hoặc liveness.
- Dashboard analytics nặng.
- Microservices.
- Kubernetes.
- Monitoring stack nặng.
