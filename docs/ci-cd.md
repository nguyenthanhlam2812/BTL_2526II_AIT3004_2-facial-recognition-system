# CI/CD Pipeline – GitHub Actions

Cập nhật: `2026-05-10`.

## Tổng quan

Mỗi khi push code lên nhánh `main` (hoặc tạo Pull Request vào `main`), GitHub Actions sẽ tự động:

1. **Chạy test** backend bằng `pytest`.
2. **Build 3 Docker images** (backend, worker, frontend).
3. **Push images** lên Docker Hub (chỉ khi push trực tiếp vào `main`, không push khi PR).

## Sơ đồ luồng hoạt động

```
Push code lên main
  └─> GitHub Actions trigger
        │
        ├─ Job 1: test
        │    ├─ Checkout code
        │    ├─ Setup Python 3.11 (có cache pip)
        │    ├─ Install dependencies
        │    ├─ Chạy pytest tests/backend
        │    └─ Nếu FAIL → dừng, không build image
        │
        └─ Job 2: build-and-push (chỉ chạy nếu Job 1 PASS)
             ├─ Checkout code
             ├─ Login Docker Hub (dùng GitHub Secrets)
             ├─ Setup Docker Buildx (hỗ trợ cache layer)
             ├─ Build & Push 3 images:
             │    - tlam281206/ai-facial-recognition-backend:latest
             │    - tlam281206/ai-facial-recognition-worker:latest
             │    - tlam281206/ai-facial-recognition-frontend:latest
             └─ Done ✓
```

## Cấu hình GitHub Secrets

Để workflow hoạt động, cần tạo 2 **Repository Secrets** trên GitHub:

1. Vào repo trên GitHub → **Settings** → **Secrets and variables** → **Actions**.
2. Bấm **New repository secret** và tạo:

| Secret Name | Giá trị | Mô tả |
|---|---|---|
| `DOCKERHUB_USERNAME` | `tlam281206` | Tên tài khoản Docker Hub |
| `DOCKERHUB_TOKEN` | *(Access Token)* | Personal Access Token từ Docker Hub |

### Cách tạo Docker Hub Access Token

1. Đăng nhập [hub.docker.com](https://hub.docker.com).
2. Bấm avatar góc trên phải → **Account Settings**.
3. Chọn **Personal access tokens** ở menu bên trái.
4. Bấm **Generate new token**.
5. Đặt tên (ví dụ: `github-actions`), chọn quyền **Read, Write, Delete**.
6. Bấm **Generate** → copy chuỗi token (chỉ hiện 1 lần duy nhất).
7. Dán chuỗi token đó vào GitHub Secret `DOCKERHUB_TOKEN`.

## Xem kết quả CI/CD

1. Vào repo trên GitHub → chọn tab **Actions**.
2. Mỗi lần push sẽ thấy 1 workflow run mới xuất hiện.
3. Bấm vào để xem chi tiết từng job (test, build-and-push).
4. Nếu thấy ✅ xanh = thành công, ❌ đỏ = có lỗi (bấm vào xem log chi tiết).

## Kiểm tra images trên Docker Hub

Sau khi workflow chạy thành công, vào [hub.docker.com/u/tlam281206](https://hub.docker.com/u/tlam281206) để xem 3 repository chứa images mới nhất.

## File liên quan

| File | Mô tả |
|---|---|
| `.github/workflows/ci.yml` | File cấu hình workflow GitHub Actions |
| `requirements/test.txt` | Dependencies riêng cho testing (pytest, httpx) |
