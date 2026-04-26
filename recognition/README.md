# Recognition Module

Thư mục này giữ logic AI có thể tái sử dụng khi đưa PoC vào backend và worker.

## Hiện có

- `pipelines/face_detect_embed.py`: detect khuôn mặt bằng InsightFace, lấy embedding, xuất JSON và ảnh annotate.

## Vai trò trong repo

- `recognition/`: logic AI dùng chung
- `scripts/poc/`: entrypoint để chạy thử nghiệm local trong Phase 2
