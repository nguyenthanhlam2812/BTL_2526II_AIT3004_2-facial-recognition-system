# Phạm vi dự án

## Bài toán

Check-in/check-out nhân viên bằng nhận diện khuôn mặt.

Phạm vi MVP:

- 1 điểm chấm công.
- 1 luồng frontend người dùng: Kiosk UI.
- 1 luồng frontend quản trị: Admin UI.
- Nhân viên nội bộ.
- Docker Compose một máy.

## Ánh xạ với đề bài

| Yêu cầu | Cách project đáp ứng |
| --- | --- |
| Frontend người dùng | Kiosk UI mở camera, gửi frame và hiển thị kết quả chấm công |
| Frontend quản trị | Admin UI: dashboard, người dùng, nhân viên, enrollment, lịch sử, báo cáo, cấu hình |
| Backend | FastAPI |
| Database | MySQL |
| Object storage | MinIO |
| Vector database | Qdrant |
| Message/event queue | Redis + RQ |
| Nginx/load balancer | Nginx trong frontend container |

## Trong phạm vi

- Admin login.
- Employee CRUD.
- Upload ảnh enrollment.
- Worker tạo embedding.
- Qdrant search embedding.
- Kiosk gửi frame check-in/check-out.
- Lưu attendance history.
- Dashboard tổng quan: stat cards (tổng NV, có mặt, đi muộn, vắng) + biểu đồ 7/30 ngày.
- Báo cáo theo ngày và export CSV.
- Quản lý admin users theo role.
- Cấu hình runtime an toàn, owner được sửa; admin/viewer xem read-only.
- Đóng gói bằng Docker Compose và image Docker Hub.

## Ngoài phạm vi

- Employee self-service portal.
- Multi-camera.
- Mobile app.
- Tính công, bảng lương, ca kíp.
- Anti-spoofing/liveness.
- Role matrix phức tạp.
- Kubernetes.
- Huấn luyện model nhận diện riêng.

## Tiêu chí MVP cuối

- Admin login được.
- Tạo/sửa/xóa nhân viên được.
- Upload enrollment được.
- Worker ghi embedding vào Qdrant được.
- Kiosk nhận diện được nhân viên đã enroll.
- Kiosk từ chối được người lạ.
- Kiosk báo được trường hợp nhiều khuôn mặt.
- History có event mới.
- Dashboard hiển thị đúng số liệu tổng quan.
- Owner sửa được cấu hình runtime an toàn; admin/viewer xem read-only.
- `docker compose up -d` chạy được full stack bằng image Docker Hub.

## Chuẩn bị demo cuối

1. Chạy `docker compose pull && docker compose up -d`, kiểm tra `docker compose ps`.
2. Dry-run đầy đủ: admin login → dashboard → tạo nhân viên → enrollment → kiosk check-in → history.
3. Chuẩn bị 3-5 ảnh enrollment rõ mặt cho người demo chính.
4. Điều chỉnh `ATTENDANCE_THRESHOLD` trong `.env.docker` nếu cần (mặc định `0.3`).
5. Nhận diện thử một lần trước demo để khởi tạo model.
