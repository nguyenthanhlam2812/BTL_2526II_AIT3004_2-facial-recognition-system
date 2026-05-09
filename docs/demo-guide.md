# Hướng dẫn demo

Tài liệu này dùng để chạy thử và demo MVP chấm công bằng nhận diện khuôn mặt.

## Chạy hệ thống

Từ thư mục gốc repo:

```powershell
docker compose pull
docker compose up -d
```

Kiểm tra container:

```powershell
docker compose ps
```

Các service cần ở trạng thái `Up`:

```text
mysql
redis
minio
qdrant
backend
worker
frontend
```

URL chính:

- Admin: [http://localhost:8080/login](http://localhost:8080/login)
- Kiosk: [http://localhost:8080/kiosk](http://localhost:8080/kiosk)
- Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Tài khoản admin mặc định:

```text
admin / admin123
```

## Luồng demo chuẩn

1. Mở `http://localhost:8080/login`, đăng nhập bằng `admin / admin123`.
2. Hệ thống chuyển sang trang **Dashboard** — hiển thị tổng quan nhân viên và biểu đồ chấm công 7 ngày.
3. Vào **Nhân viên**, tạo hoặc kiểm tra nhân viên demo.
4. Vào **Enrollment** của nhân viên, upload 3-5 ảnh rõ mặt.
5. Đợi job enrollment chuyển sang trạng thái thành công.
6. Mở trang kiosk (`http://localhost:8080/kiosk`) — giao diện dark mode với camera scan animation.
7. Cho phép trình duyệt truy cập camera.
8. Chọn `Check-in` hoặc `Check-out`.
9. Đưa một khuôn mặt vào khung hình và bấm **Nhận diện**.
10. Kết quả hiện ngay trên overlay (ghi nhận / không nhận ra / nhiều khuôn mặt).
11. Quay lại Admin → **Chấm công** để kiểm tra bản ghi mới, hoặc xem Dashboard để thấy số liệu cập nhật.

## Chuẩn bị ảnh enrollment

Nên dùng ít nhất 3 đến 5 ảnh cho mỗi nhân viên:

- Ảnh chính diện.
- Ảnh quay nhẹ sang trái.
- Ảnh quay nhẹ sang phải.
- Ảnh trong điều kiện ánh sáng gần giống lúc demo.
- Ảnh không bị mờ, không che quá nhiều khuôn mặt.

Tránh dùng ảnh có nhiều khuôn mặt trong cùng khung hình. Nếu nhân viên hay đeo kính lúc demo, nên có ảnh enrollment cũng đeo kính.

## Cách đứng trước camera

Để nhận diện ổn hơn:

- Chỉ để một người trong khung hình.
- Đưa mặt vào giữa khung hình — các góc bracket sẽ sáng lên khi hệ thống đang nhận diện.
- Giữ khoảng cách vừa phải với camera.
- Tránh ánh sáng quá gắt sau lưng.
- Nhìn tương đối thẳng vào camera trong 1 đến 2 giây.

Nếu đổi góc mặt nhiều hoặc ánh sáng thay đổi mạnh, hệ thống có thể trả `unknown_face`. Đây là giới hạn bình thường của MVP và cần tuning thêm bằng dữ liệu demo tốt hơn.

## Lỗi thường gặp

### Lần đầu nhận diện rất lâu

Nguyên nhân thường là backend đang tải hoặc khởi tạo model InsightFace lần đầu.

Cách xử lý:

```powershell
docker compose logs backend --tail=100
```

Nếu log đang hiện tiến trình tải model, đợi tải xong rồi bấm nhận diện lại. Model được cache trong Docker volume `insightface_models`, nên các lần chạy sau thường không cần tải lại nếu không xoá volume.

Không dùng lệnh này nếu muốn giữ cache model:

```powershell
docker compose down -v
```

### Không nhận ra khuôn mặt

Nguyên nhân thường gặp:

- Ảnh enrollment chưa đủ đa góc.
- Khuôn mặt trong camera quá tối, quá xa hoặc bị mờ.
- Góc mặt lúc demo khác nhiều so với ảnh enrollment.
- Threshold nhận diện đang chặt.

Cách xử lý nhanh:

- Enroll thêm ảnh rõ và đa góc hơn.
- Đứng gần camera hơn.
- Giảm ánh sáng nền phía sau.
- Test lại với mặt nhìn thẳng.
- Nếu người đã enroll vẫn thường bị `unknown_face`, thử đặt `ATTENDANCE_THRESHOLD` trong `.env.docker` khoảng `0.28` đến `0.35`.
- Nếu hệ thống nhận nhầm người lạ, tăng `ATTENDANCE_THRESHOLD` lên cao hơn.

### Báo nhiều khuôn mặt

Nguyên nhân là detector thấy hơn một khuôn mặt hoặc vùng giống khuôn mặt trong khung hình.

Cách xử lý:

- Chỉ để một người trước camera.
- Dọn nền phía sau nếu có ảnh người, poster hoặc màn hình khác.
- Đưa mặt demo vào giữa khung hình.

### Camera không mở

Cách xử lý:

- Cho phép quyền camera trong trình duyệt.
- Đóng ứng dụng khác đang dùng webcam.
- Reload lại trang kiosk.
- Thử lại bằng Chrome hoặc Edge.

### Enrollment không chạy

Kiểm tra worker:

```powershell
docker compose logs worker --tail=100
```

Worker đúng sẽ có dòng:

```text
Listening on enrollment...
```

## Checklist trước khi demo

- `docker compose ps` hiển thị đủ service `Up`.
- Mở được `http://localhost:8080/login`.
- Đăng nhập được bằng `admin / admin123`, hệ thống chuyển sang Dashboard.
- Dashboard hiển thị số liệu nhân viên và biểu đồ.
- Có ít nhất một nhân viên đã enrollment thành công.
- Mở được `http://localhost:8080/kiosk` — thấy giao diện dark, camera scan animation.
- Camera được cấp quyền, trạng thái hiện "Camera sẵn sàng".
- Nhận diện thử một lần trước khi demo chính thức để warm-up model.
- Lịch sử chấm công hiển thị event mới sau khi kiosk ghi nhận.
