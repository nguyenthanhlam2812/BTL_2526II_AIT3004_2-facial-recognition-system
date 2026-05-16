# Pipeline CI/CD

## Tổng quan

Mỗi khi push code lên `main` hoặc tạo pull request vào `main`, GitHub Actions sẽ:

1. Chạy backend tests bằng `pytest`
2. Chạy `npm run lint` và `npm run build` cho frontend
3. Kiểm tra cấu hình Docker Compose cho:
   - stack mặc định
   - stack tunnel public qua `docker-compose.tunnel.yml`
4. Build đủ 3 Docker image: backend, worker, frontend
5. Đẩy image lên Docker Hub chỉ khi push trực tiếp vào `main`
6. Smoke-test lại đúng đường nộp bài trên runner sạch bằng `docker compose pull` và `docker compose up -d`

## Luồng hoạt động

```text
Push/PR vào main
  -> backend-tests
       -> pip install requirements/backend.txt + requirements/test.txt
       -> pytest tests/backend
  -> frontend-check
       -> npm ci
       -> npm run lint
       -> npm run build
  -> compose-config
       -> docker compose config
       -> docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel config
  -> docker-images
       -> build image backend/worker/frontend
       -> push lên Docker Hub nếu đây là push vào main
  -> dockerhub-smoke (chỉ khi push vào main)
       -> docker compose pull
       -> docker compose up -d
       -> health/login/settings OK
       -> direct backend /attendance/frame không có token => 401
       -> frontend proxy /attendance/frame vẫn gọi được kiosk flow
```

## GitHub Secrets

Để push image lên Docker Hub, repo cần:

| Secret Name | Giá trị |
| --- | --- |
| `DOCKERHUB_USERNAME` | `tlam281206` |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

## File liên quan

| File | Mô tả |
| --- | --- |
| `.github/workflows/ci.yml` | Workflow GitHub Actions |
| `docker-compose.yml` | Base stack |
| `docker-compose.tunnel.yml` | Public demo tunnel override |
| `docker-compose.build.yml` | Override build từ mã nguồn local |
