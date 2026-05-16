# Mô-đun nhận diện

Thư mục này giữ PoC và logic AI dùng chung cho backend/worker.

## File chính

- `pipelines/face_detect_embed.py`: detect mặt, lấy embedding, xuất annotate và JSON.
- `pipelines/cosine_similarity_eval.py`: tính cosine similarity và gợi ý threshold PoC.
- `models.md`: ghi lựa chọn model hiện tại.

## Vai trò

- `recognition/`: logic AI dùng chung.
- `scripts/poc/`: entrypoint chạy PoC local.
