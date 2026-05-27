# Demo guide

Tài liệu này dùng để dry-run trước khi bảo vệ và làm script nói khi demo.

## Chuẩn bị

Yêu cầu:

- Docker Desktop đang chạy.
- Webcam hoạt động.
- Trình duyệt cho phép camera trên `localhost` hoặc HTTPS.
- Một vài ảnh rõ mặt để dự phòng nếu webcam lỗi.

Chạy stack:

```powershell
docker compose pull
docker compose up -d
```

Kiểm tra nhanh:

```powershell
docker compose ps
Invoke-WebRequest http://localhost:8000/healthz
Invoke-WebRequest http://localhost:8080/healthz
```

Tài khoản local:

```text
admin / admin123
```

Nếu DB volume đã từng đổi mật khẩu, dùng mật khẩu hiện tại thay vì `admin123`. Khi public demo bằng `.env.docker`, dùng password demo đã đổi trong file local đó.

## Dữ liệu demo nên có

Chuẩn bị trước:

- 1 owner mặc định: `admin`.
- 1 admin demo: `hr-admin`.
- 1 viewer demo: `auditor`.
- 2-3 phòng ban: `Software Engineering`, `Quality Assurance`, `IT Operations`.
- 2-3 chức vụ: `Software Engineer`, `QA Engineer`, `System Administrator`.
- 1 nhân viên có ảnh enrollment rõ mặt.
- 1 người lạ hoặc ảnh người lạ để test `unknown_face`.

Nếu cần reset data khi tập demo, ưu tiên dùng UI xóa event/chỉnh trạng thái. Chỉ xóa volume DB khi muốn dựng lại từ đầu.

## Flow demo 5-7 phút

### 1. Giới thiệu kiến trúc

Mở README hoặc [diagrams.md](diagrams.md), nói ngắn:

> Hệ thống là full-stack AI attendance. Kiosk gửi frame camera, backend nhận diện, Qdrant lưu embedding, MySQL lưu nghiệp vụ, MinIO lưu ảnh enrollment, Redis/RQ xử lý job nền và Nginx đứng trước toàn bộ stack.

### 2. Đăng nhập và dashboard

Mở:

```text
http://localhost:8080/login
```

Đăng nhập `admin / admin123`. Chỉ vào dashboard:

- Tổng nhân viên.
- Có mặt hôm nay.
- Đi muộn.
- Vắng mặt.
- Biểu đồ 7/30 ngày.

Câu thoại:

> Dashboard không tự tính ở frontend. Backend aggregate theo timezone nghiệp vụ nên Dashboard và Báo cáo dùng chung nguồn dữ liệu.

### 3. Danh mục và nhân viên

Vào `Danh mục`, tạo hoặc chỉ các phòng ban/chức vụ có sẵn.

Vào `Nhân viên`, tạo employee:

```text
Mã: EMP001
Họ tên: Nguyen Van A
Phòng ban: Software Engineering
Chức vụ: Software Engineer
Trạng thái: Hoạt động
```

Câu thoại:

> Department và position không còn nhập tự do hoàn toàn. Người vận hành chọn từ danh mục để tránh dữ liệu bị lệch như IT, I.T., Information Technology.

### 4. Enrollment

Ở nhân viên vừa tạo, bấm enroll.

Demo tốt nhất:

- Camera mode.
- Chụp 3 góc: front, left, right.
- Đợi job thành `success`.

Nếu webcam lỗi:

- Dùng upload mode với 1-5 ảnh rõ mặt.

Câu thoại:

> Enrollment chạy nền qua Redis/RQ. Người dùng không phải chờ API xử lý ảnh xong trong request chính.

### 5. Kiosk check-in/check-out

Mở:

```text
http://localhost:8080/kiosk
```

Cho phép camera, đưa mặt vào khung và check-in.

Các case nên demo:

- Một người đã enroll: `recorded`.
- Người lạ hoặc ảnh không match: `unknown_face`.
- Hai người cùng xuất hiện: `multiple_faces` nếu setup được.

Lưu ý khi muốn có bằng chứng trong `Chấm công`: auto scan gửi frame lỗi với `record_unmatched=false` để giảm nhiễu log. Khi demo `unknown_face` hoặc `multiple_faces`, hãy bấm quét thủ công để backend ghi event lỗi vào lịch sử.

Câu thoại:

> Kiosk dùng chung tại văn phòng. Nhân viên không đăng nhập cá nhân; hệ thống nhận diện khuôn mặt và tự quyết định event.

### 6. Lịch sử, báo cáo, export

Vào `Chấm công`:

- Lọc trạng thái nhận diện.
- Xem event vừa tạo.
- Export CSV nếu cần.

Vào `Báo cáo`:

- Xem báo cáo ngày (cột `Check-in đầu`, `Check-out cuối`, `Giờ làm`, `Trạng thái`).
- Click icon `▸` bên trái mỗi row để xem **chi tiết session pair-matched** trong ngày (sáng-chiều có nghỉ trưa, OT đêm…).
- Cột `Giờ làm` chỉ cộng các session đã hoàn tất (`is_complete=true`); session chưa có check-out không tính.
- Lọc phòng ban/status.
- Export CSV.

Câu thoại về 2 cách tính:

> Báo cáo ngày dùng "bracketing" — chỉ lấy check-in sớm nhất và check-out muộn nhất, đơn giản cho HR check đi muộn/vắng mặt. Sessions report ghép cặp greedy các event in-out thành N work session/ngày, dùng cho tính giờ làm thực tế trừ giờ nghỉ giữa các session. Endpoint `/api/attendance/reports/sessions` expose dữ liệu này, frontend show qua expandable row.

### 7. Audit và phân quyền

Vào `Nhật ký` bằng owner:

- Chỉ event tạo nhân viên, enrollment, xóa/sửa attendance, settings, user action.

Đăng nhập viewer:

- Viewer không thấy `Người dùng`, `Cấu hình`, `Nhật ký`.
- Viewer chỉ xem, không tạo/sửa/xóa.

Câu thoại:

> Role được chia theo vận hành nội bộ: owner là system admin, admin là HR/operator, viewer là auditor read-only.

## Public demo

Nếu cần public demo, dùng `.env.docker` và đổi secret trước:

```env
PUBLIC_DEMO_MODE=true
SEED_ADMIN_PASSWORD=replace-with-strong-password
JWT_SECRET_KEY=replace-with-long-random-secret
KIOSK_API_TOKEN=replace-with-strong-kiosk-token
```

Ngrok Free:

```powershell
docker compose --env-file .env.docker -f docker-compose.yml -f docker-compose.ngrok.yml --profile ngrok up -d
```

Lấy URL public Ngrok:

```powershell
(Invoke-RestMethod http://localhost:4040/api/tunnels).tunnels | Select-Object -ExpandProperty public_url
```

Flow public demo bằng Ngrok:

1. Chạy stack bằng lệnh Ngrok Free ở trên.
2. Mở `http://localhost:4040` hoặc gọi API tunnels để lấy URL HTTPS.
3. Mở `<public-url>/login`, đăng nhập bằng password demo đã đổi trong `.env.docker`.
4. Mở `<public-url>/kiosk`, cấp quyền camera và test check-in.
5. Không chia sẻ URL public nếu `.env.docker` vẫn dùng password/token mặc định.

Ngrok free thường cấp URL ngẫu nhiên và URL có thể đổi sau mỗi lần restart. Camera hoạt động tốt hơn trên public HTTPS origin. Nếu trình duyệt hiện trang cảnh báo miễn phí của Ngrok ở lần mở đầu tiên, chọn tiếp tục vào site demo sau khi kiểm tra URL đúng là URL vừa lấy từ `localhost:4040`.

Nếu vừa sửa frontend/backend local và muốn public URL cập nhật ngay như `localhost:5173`, build lại stack public từ source:

```powershell
docker compose --env-file .env.docker -f docker-compose.yml -f docker-compose.build.yml -f docker-compose.ngrok.yml --profile ngrok up -d --build backend worker frontend nginx ngrok
```

## Q&A nên chuẩn bị

**Kiosk là app chung hay mỗi nhân viên tự mở web?**
Kiosk là điểm chấm công chung đặt tại văn phòng. Nhân viên không đăng nhập, chỉ đứng trước camera. Admin console mới cần tài khoản.

**Nếu người khác bật kiosk thì có chấm công được không?**
Kiosk chỉ gửi frame. Backend chỉ ghi nhận nếu khuôn mặt match employee active và vượt threshold. Người lạ trả `unknown_face`.

**Viewer để làm gì?**
Viewer dành cho người chỉ cần xem dữ liệu, ví dụ auditor hoặc quản lý chỉ xem báo cáo. Viewer không sửa cấu hình, user, nhân viên hoặc event.

**Xóa nhân viên rồi báo cáo có mất không?**
Mặc định hệ thống chặn xóa employee nếu đã có enrollment hoặc attendance. Với nhân viên nghỉ việc, chuyển trạng thái `Tạm ngưng` để giữ lịch sử báo cáo. Nếu cần xóa cả dữ liệu khuôn mặt (ví dụ yêu cầu xóa theo Nghị định 13/2023 về dữ liệu cá nhân), Owner có thể tick "Xóa vĩnh viễn" trong modal xóa: hệ thống drop embedding khỏi Qdrant, xóa ảnh enrollment trên MinIO và đặt `employee_id` của các event chấm công liên quan về NULL. Lịch sử chấm công vẫn còn ở dạng ẩn danh, aggregate báo cáo theo nhân viên thì không còn.

**Đưa ảnh hoặc video trước camera thì sao?**
Bản demo có quality gate và enrollment 3 góc, nhưng chưa phải chống giả mạo production-grade. Nếu dùng thật cần model anti-spoofing chuyên dụng, camera depth hoặc challenge-response.

**Tại sao có cả MinIO và Qdrant?**
MinIO lưu ảnh enrollment gốc; Qdrant lưu vector embedding để search khuôn mặt nhanh. Hai loại lưu trữ phục vụ hai mục đích khác nhau.

**Queue dùng để làm gì?**
Enrollment tạo embedding có thể chậm, nên chạy nền qua Redis/RQ. API trả `job_id`, worker xử lý sau và cập nhật trạng thái.

**Nếu Redis lỗi thì sao?**
Enrollment queue sẽ bị ảnh hưởng. Với duplicate gate của attendance, code ưu tiên fail-open để không chặn chấm công, nhưng khả năng chống ghi trùng tạm thời giảm.

**Real-time ở đây nghĩa là gì?**
Kiosk hiển thị camera live, frontend phát hiện mặt cục bộ liên tục và gửi frame định kỳ lên backend để nhận diện. Đây là near real-time frame scanning, không phải stream video WebSocket/WebRTC.

**Vì sao frontend người dùng và frontend admin chỉ có một image?**
Hai giao diện là hai route/module riêng trong cùng React SPA image: `/kiosk` cho người dùng tại kiosk và `/login`/`/admin/*` cho quản trị. Đề yêu cầu đủ frontend surface, không bắt buộc tách thành hai image.

**Vì sao MinIO chưa lưu snapshot chấm công?**
MinIO đang dùng để lưu ảnh enrollment gốc; snapshot chấm công là hướng mở rộng và bucket `snapshots` đã để sẵn. Phạm vi bản nộp tập trung vào enrollment, embedding và attendance event.

## Lỗi hay gặp

| Triệu chứng | Cách xử lý |
| --- | --- |
| Login không được bằng `admin/admin123` | DB đã có user và password từng bị đổi. Dùng password hiện tại hoặc reset DB demo. |
| Kiosk không mở camera | Kiểm tra quyền camera của browser, dùng `localhost` hoặc HTTPS. |
| Frame direct tới `:8000` bị 401 | Đây là đúng. Gọi qua `:8080/kiosk` để Nginx inject token. |
| Enrollment lâu ở lần đầu | Model AI có thể đang tải/warm-up. Đợi log backend/worker ổn định. |
| Nhân viên tạo xong không match | Kiểm tra enrollment job đã `success`, employee active, threshold phù hợp. |
| Danh mục báo trùng | Tên được normalize và unique; dùng tên khác hoặc sửa item cũ. |
| Chạy Ngrok báo thiếu `NGROK_AUTHTOKEN` | Lấy token trong Ngrok dashboard và đặt vào `.env.docker`, không đặt vào `.env.docker.example`. |
| URL Ngrok cũ không mở được | Ngrok free đổi URL sau restart; lấy URL mới từ `http://localhost:4040/api/tunnels` hoặc log container `ngrok`. |
| Trình duyệt hiện cảnh báo Ngrok | Đây là warning của free tunnel. Kiểm tra đúng URL vừa lấy từ `localhost:4040`, rồi chọn tiếp tục vào site demo. |
| Public URL mở được nhưng camera không bật | Dùng URL HTTPS của Ngrok, kiểm tra quyền camera của browser và tránh iframe/proxy khác. |
| Public demo login không khớp password mới | DB volume đã có user cũ nên seed không ghi đè. Dùng password hiện tại hoặc reset volume demo có chủ đích. |
| `localhost:5173` có chức năng mới nhưng `localhost:8080` vẫn cũ | `5173` là Vite dev server, `8080` là Docker image đã build. Chạy lại `docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build backend worker frontend nginx`. |

## Checklist dry-run

- [ ] `docker compose ps` tất cả service healthy/running.
- [ ] Login owner thành công.
- [ ] Tạo danh mục, nhân viên, enrollment thành công.
- [ ] Kiosk match được nhân viên đã enroll.
- [ ] Kiosk trả `unknown_face` cho người lạ.
- [ ] Chấm công lọc được `recorded`, `unknown_face`, `multiple_faces`.
- [ ] Báo cáo ngày và export CSV hoạt động, expandable row hiện session pair-matched.
- [ ] Audit log có event thao tác.
- [ ] Viewer không có quyền ghi.
- [ ] Nếu public demo bằng Ngrok: `localhost:4040/api/tunnels` có HTTPS URL và `/login`, `/kiosk` load được qua URL đó.
