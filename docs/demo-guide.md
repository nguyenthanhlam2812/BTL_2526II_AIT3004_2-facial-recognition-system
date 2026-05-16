# Hướng dẫn demo

## Chạy hệ thống

```powershell
docker compose pull
docker compose up -d
```

Nếu cần smoke-test code local thay vì image Docker Hub:

```powershell
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build backend worker frontend
```

URL chính:

- Admin: [http://localhost:8080/login](http://localhost:8080/login)
- Kiosk: [http://localhost:8080/kiosk](http://localhost:8080/kiosk)
- Tài liệu API: [http://localhost:8000/docs](http://localhost:8000/docs)

Tài khoản admin mặc định cho local:

```text
admin / admin123
```

## Public demo qua Cloudflare Tunnel

Checklist trước khi bật tunnel:

- Tạo hoặc sửa `.env.docker`
- Đổi `SEED_ADMIN_PASSWORD`
- Đổi `JWT_SECRET_KEY`
- Đổi `KIOSK_API_TOKEN`
- Xác nhận `docker compose ps` cho thấy stack local đang ổn định

Sau đó chạy:

```powershell
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel up -d
```

Nếu cần build từ mã nguồn local rồi mở tunnel:

```powershell
docker compose -f docker-compose.yml -f docker-compose.build.yml -f docker-compose.tunnel.yml --profile tunnel up -d --build backend worker frontend tunnel
```

## Luồng demo chuẩn

1. Mở `http://localhost:8080/login`, đăng nhập.
2. Vào Dashboard để xem tổng nhân viên, có mặt, đi muộn, vắng mặt và biểu đồ 7/30 ngày.
3. Vào Người dùng, tạo thử tài khoản `viewer` hoặc `admin` phụ nếu cần demo phân quyền.
4. Vào Cấu hình để đổi mật khẩu admin và sửa threshold/timezone an toàn nếu cần.
5. Vào Nhân viên, tạo nhân viên mới nếu cần.
6. Vào Enrollment của nhân viên, upload 3-5 ảnh rõ mặt.
7. Đợi job enrollment thành công.
8. Mở `http://localhost:8080/kiosk`, cho phép camera.
9. Chọn `Check-in` hoặc `Check-out`.
10. Đưa mặt vào khung hình, kiosk sẽ tự quét.
11. Quay lại Admin -> Chấm công để xem sự kiện thô.
12. Vào Báo cáo để xem tổng hợp theo ngày và export CSV.

## Ghi chú về báo cáo

- Múi giờ nghiệp vụ: `Asia/Ho_Chi_Minh`
- Quy tắc đi muộn: `first_check_in > 09:00`
- Dashboard và Báo cáo dùng cùng nguồn dữ liệu từ backend
- Report/export bị giới hạn 31 ngày mỗi request

## Xử lý lỗi thường gặp

### Lần đầu nhận diện lâu

Backend có thể đang khởi tạo model InsightFace.

```powershell
docker compose logs backend --tail=100
```

### Không nhận ra khuôn mặt

- Thêm ảnh enrollment đa góc hơn
- Đứng gần camera hơn
- Giảm ánh sáng nền phía sau
- Kiểm tra `ATTENDANCE_THRESHOLD` nếu cần

### Camera không mở

- Cho phép camera trong trình duyệt
- Đóng ứng dụng khác đang dùng webcam
- Reload kiosk page

### Worker không xử lý enrollment

```powershell
docker compose logs worker --tail=100
```

## Checklist trước khi demo

- `docker compose ps` hiển thị đủ service `Up`
- Đăng nhập được vào Admin
- Trang Người dùng tạo/sửa quyền/reset mật khẩu được với owner
- Cấu hình hệ thống lưu/reset cấu hình an toàn được với owner
- Có ít nhất một nhân viên enroll thành công
- Kiosk mở được camera
- Dashboard có dữ liệu
- Báo cáo mở được và export CSV được
- Direct `POST http://127.0.0.1:8000/api/attendance/frame` không có `X-Kiosk-Token` bị `401`
- `POST http://127.0.0.1:8080/api/attendance/frame` qua frontend vẫn hoạt động vì Nginx inject token
- Nếu bật tunnel public, `.env.docker` đã đổi password admin, JWT secret và kiosk token trước khi chạy lệnh tunnel
