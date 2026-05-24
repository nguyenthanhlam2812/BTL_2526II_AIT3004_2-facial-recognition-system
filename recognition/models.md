# Mô hình nhận diện

## Lựa chọn hiện tại

- Library: `InsightFace`.
- Model pack: `buffalo_l`.
- Môi trường ưu tiên: CPU-first.
- Attendance threshold mặc định: `0.3`.
- Duplicate enrollment threshold mặc định: `0.6`.

## Lý do chọn

- Đủ tốt cho demo MVP.
- Dễ dùng trong PoC, backend và worker.
- Không cần train model riêng ở giai đoạn hiện tại.

## Luồng sử dụng trong hệ thống

1. Backend hoặc worker nhận ảnh JPEG/PNG.
2. InsightFace detect mặt và tạo embedding cho mặt chính.
3. Worker ghi embedding enrollment vào Qdrant collection `employee_faces`.
4. Kiosk gửi frame; backend tạo embedding mới, search Qdrant và so score với `attendance_threshold`.
5. Nếu match employee active đủ ngưỡng, backend ghi attendance event `recorded`; nếu không thì trả `unknown_face` hoặc `multiple_faces`.

Frontend kiosk dùng MediaPipe BlazeFace để gate camera trước khi gửi frame. Quyết định nhận diện cuối cùng vẫn nằm ở backend với InsightFace/Qdrant.

## Threshold và đánh giá

- `ATTENDANCE_THRESHOLD=0.3` là default runtime, có thể chỉnh trong trang owner-only `Cấu hình`.
- `DUPLICATE_ENROLL_THRESHOLD=0.6` dùng để chặn cùng một khuôn mặt bị enroll cho nhân viên khác.
- `recognition/pipelines/cosine_similarity_eval.py` dùng để đánh giá cặp ảnh local và gợi ý threshold từ dữ liệu demo.
- Khi demo thực tế, nên enroll 3 góc bằng camera trong cùng điều kiện ánh sáng với kiosk để tăng độ ổn định.

## Giới hạn

- Chưa có production-grade anti-spoofing/liveness.
- Accuracy phụ thuộc camera, ánh sáng, góc mặt, số ảnh enrollment và threshold.
- Ảnh in hoặc video chất lượng cao vẫn cần model chống giả mạo chuyên dụng, camera depth hoặc challenge-response nếu triển khai thật.

## File liên quan

- `recognition/pipelines/face_detect_embed.py`
- `recognition/pipelines/cosine_similarity_eval.py`

## Hướng sau này

Nếu cần mở rộng, có thể tách logic thành `detect.py`, `embed.py`, `similarity.py`, `threshold.py`. Hiện tại chưa ưu tiên vì MVP cần hoàn thiện frontend và Docker trước.
