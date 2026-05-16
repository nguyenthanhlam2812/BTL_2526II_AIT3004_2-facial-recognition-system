# AI Facial Recognition Attendance

MVP chấm công nhân viên bằng nhận diện khuôn mặt. Bản nộp hướng tới việc giảng viên chỉ cần chạy hệ thống bằng Docker Compose.

## Chạy bản nộp

Yêu cầu:

- Docker Desktop
- Git

Lệnh chạy:

```powershell
docker compose pull
docker compose up -d
```

Nếu máy chưa có image local, `docker compose up -d` cũng sẽ tự kéo image từ Docker Hub.

Các URL chính:

- Frontend: [http://localhost:8080](http://localhost:8080)
- Admin: [http://localhost:8080/login](http://localhost:8080/login)
- Kiosk: [http://localhost:8080/kiosk](http://localhost:8080/kiosk)
- Backend docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- MinIO console: [http://localhost:9001](http://localhost:9001)

Tài khoản admin mặc định:

```text
admin / admin123
```

## Ánh xạ yêu cầu đề bài

| Yêu cầu | Triển khai trong project |
| --- | --- |
| Frontend người dùng | Kiosk UI: camera, check-in/check-out, hiển thị kết quả nhận diện |
| Frontend quản trị | Admin UI: login, quản lý nhân viên, enrollment, lịch sử chấm công, cấu hình read-only |
| Backend | FastAPI |
| Database | MySQL |
| Object storage | MinIO |
| Vector database | Qdrant |
| Message/event queue | Redis + RQ worker |
| Load balancer/Nginx | Nginx nằm trong frontend container, phục vụ SPA và proxy `/api` tới backend |

## Docker Hub

Ba image chính:

```text
tlam281206/ai-facial-recognition-backend:latest
tlam281206/ai-facial-recognition-worker:latest
tlam281206/ai-facial-recognition-frontend:latest
```

Build local và tag image:

```powershell
docker compose -f docker-compose.yml -f docker-compose.build.yml build
```

Push lên Docker Hub:

```powershell
docker login
docker push tlam281206/ai-facial-recognition-backend:latest
docker push tlam281206/ai-facial-recognition-worker:latest
docker push tlam281206/ai-facial-recognition-frontend:latest
```

## Luồng demo chính

1. Đăng nhập admin.
2. Tạo nhân viên.
3. Upload 3-5 ảnh enrollment rõ mặt cho nhân viên.
4. Đợi job enrollment hoàn thành.
5. Mở kiosk, cho phép camera, thực hiện check-in hoặc check-out.
6. Kiểm tra bản ghi ở trang lịch sử chấm công.

## Kiểm tra nhanh

```powershell
docker compose ps
docker compose logs backend --tail=100
docker compose logs worker --tail=100
```

Healthcheck:

```powershell
Invoke-WebRequest http://localhost:8080/healthz
```

## Công nghệ chính

- Backend: FastAPI, SQLAlchemy, Alembic
- Frontend: React, Vite, TypeScript, Mantine
- AI: InsightFace
- Database: MySQL
- Queue: Redis, RQ
- Object storage: MinIO
- Vector search: Qdrant
- Runtime: Docker Compose, Nginx trong frontend container

## Cấu trúc repo

```text
backend/          FastAPI app
worker/           RQ worker xử lý enrollment
frontend/         React admin UI và kiosk UI
recognition/      Logic AI dùng chung
scripts/          Script seed và PoC
tests/            Backend tests
docs/             Tài liệu kỹ thuật
requirements/     Python dependencies theo vai trò
docker-compose.yml
docker-compose.build.yml
```

## Test

Backend:

```powershell
.\.venv\Scripts\python -m pytest tests\backend -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

## Lưu ý repo

Repo không commit các file môi trường và dữ liệu cá nhân:

- `.env`
- `.env.docker`
- ảnh demo/enrollment cá nhân
- output phân tích local trong `artifacts/`

Các file mẫu như `.env.example` và `.env.docker.example` được commit để người khác cấu hình lại.

## Tài liệu

- `docs/project-scope.md`: phạm vi và tiêu chí MVP.
- `docs/architecture.md`: kiến trúc hệ thống.
- `docs/api-contract.md`: contract API.
- `docs/database-setup.md`: cấu hình database local và Docker.
- `docs/demo-data.md`: dữ liệu demo và lưu ý consent.
- `docs/demo-guide.md`: hướng dẫn demo và xử lý lỗi thường gặp.
- `docs/diagrams.md`: sơ đồ hệ thống.
