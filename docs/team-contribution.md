# Phân công công việc nhóm

## Thông tin nhóm

| Thành viên | Mã sinh viên | Vai trò chính | Tỷ lệ đóng góp dự kiến |
| --- | --- | --- | --- |
| Nguyễn Thành Lâm | 24022378 | Full-stack implementation, AI pipeline, deployment, testing kỹ thuật | 65% |
| Đỗ Mạnh Quân | 24022432 | Slide/report, tài liệu trình bày, kịch bản demo, manual review | 35% |

## Bảng phân công chi tiết

| Hạng mục | Phụ trách chính | Phối hợp | Nội dung thực hiện |
| --- | --- | --- | --- |
| Phân tích yêu cầu và thiết kế nghiệp vụ | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Xác định actor, use case, luồng admin tạo nhân viên, enrollment khuôn mặt, kiosk chấm công và báo cáo attendance. |
| Thiết kế kiến trúc hệ thống | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Thiết kế kiến trúc FastAPI, React, MySQL, Redis/RQ worker, MinIO, Qdrant, Nginx và Docker Compose. |
| Backend API | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Xây dựng API xác thực, quản lý nhân viên, phòng ban/chức vụ, enrollment, attendance, audit log và cấu hình hệ thống. |
| Cơ sở dữ liệu và migration | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Thiết kế schema MySQL, quan hệ foreign key, Alembic migration, seed user, seed danh mục phòng ban/chức vụ. |
| AI và xử lý khuôn mặt | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Tích hợp InsightFace, OpenCV, tạo embedding, tìm kiếm vector bằng Qdrant, xử lý duplicate face và cleanup dữ liệu biometric. |
| Queue và worker nền | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Xây dựng Redis/RQ job cho enrollment bất đồng bộ, xử lý ảnh enrollment và cập nhật trạng thái kết quả. |
| Frontend Admin UI | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Xây dựng giao diện đăng nhập, dashboard, quản lý nhân viên, enrollment, attendance, audit log và system settings. |
| Kiosk chấm công | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Xây dựng giao diện kiosk dùng camera, MediaPipe face detection, gửi frame về backend và hiển thị kết quả chấm công. |
| Bảo mật và phân quyền | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Cài đặt JWT, role owner/admin/operator, kiosk token, rate limiting và audit log cho thao tác quản trị. |
| Docker và triển khai demo | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Cấu hình Docker Compose, Nginx reverse proxy, Docker Hub image, Ngrok public HTTPS demo và biến môi trường chạy demo. |
| CI/CD và kiểm thử tự động | Nguyễn Thành Lâm | Đỗ Mạnh Quân | Cấu hình GitHub Actions, backend pytest, frontend Vitest/lint/build, smoke test Docker Compose. |
| Report và slide giới thiệu | Đỗ Mạnh Quân | Nguyễn Thành Lâm | Chuẩn bị nội dung báo cáo, single-page slide, tóm tắt mục tiêu hệ thống, stack công nghệ, thành viên và kịch bản trình bày. |
| Tài liệu demo và kiểm thử thủ công | Đỗ Mạnh Quân | Nguyễn Thành Lâm | Review README/demo guide, kiểm tra checklist demo, chuẩn bị ảnh/video minh họa, chạy thử các kịch bản trước buổi bảo vệ. |

## Kết quả đóng góp theo module

- Nguyễn Thành Lâm: phụ trách chính phần hiện thực hệ thống, gồm backend FastAPI, frontend React/Vite, kiosk camera, AI recognition pipeline, MySQL schema, Redis/RQ worker, MinIO, Qdrant, Docker Compose, Ngrok và test kỹ thuật.
- Đỗ Mạnh Quân: phụ trách chính phần trình bày và đóng gói bài nộp, gồm report, slide một trang, kịch bản demo, review tài liệu, chuẩn bị minh họa và kiểm thử thủ công theo checklist.


