# Tech Stack

## Mục đích

Tài liệu này chốt stack chính và stack dự phòng để nhóm không đổi công nghệ tùy hứng khi sang các phase tiếp theo.

## Stack chính

| Thành phần | Lựa chọn | Ghi chú |
| --- | --- | --- |
| Frontend | React + Vite + TypeScript | 1 app, 2 route: `/admin` và `/kiosk` |
| Backend | FastAPI | Monolith, phục vụ API và attendance flow |
| AI | InsightFace + OpenCV | Detect + embedding theo hướng CPU-first |
| Database | MySQL | Lưu users, employees, enrollments, attendance events |
| Vector DB | Qdrant | Lưu face embeddings, query top-k |
| Object Storage | MinIO | Lưu ảnh đăng ký và snapshot |
| Queue | Redis + RQ | Phương án chính để nộp bài |
| Reverse Proxy | nginx | Điều phối frontend và backend |
| Orchestration | Docker Compose | Single-node, phục vụ demo và chấm bài |

## Stack dự phòng

| Hạng mục | Fallback | Khi nào dùng |
| --- | --- | --- |
| Frontend | HTML/JS đơn giản hoặc FastAPI templates | Khi React làm chậm tiến độ hoặc thiếu người |
| Queue local dev | FastAPI `BackgroundTasks` | Chỉ dùng để debug hoặc cứu local dev, không phải phương án nộp chính |
| AI library | Thư viện nhẹ hơn nếu cần | Khi image AI quá nặng hoặc build Docker không ổn định |

## Quy tắc chốt stack

- Không đổi database, vector DB, object storage và queue sau Phase 2 nếu không có blocker rõ ràng.
- Không tách microservice trong MVP.
- Không thêm Kubernetes, monitoring stack hoặc hạ tầng production phức tạp.
- Mọi thay đổi stack phải có lý do kỹ thuật rõ và được cập nhật lại docs.
