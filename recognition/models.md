# Mô hình nhận diện

## Lựa chọn hiện tại

- Library: `InsightFace`.
- Model pack: `buffalo_l`.
- Môi trường ưu tiên: CPU-first.

## Lý do chọn

- Đủ tốt cho demo MVP.
- Dễ dùng trong PoC, backend và worker.
- Không cần train model riêng ở giai đoạn hiện tại.

## File liên quan

- `recognition/pipelines/face_detect_embed.py`
- `recognition/pipelines/cosine_similarity_eval.py`

## Hướng sau này

Nếu cần mở rộng, có thể tách logic thành `detect.py`, `embed.py`, `similarity.py`, `threshold.py`. Hiện tại chưa ưu tiên vì MVP cần hoàn thiện frontend và Docker trước.
