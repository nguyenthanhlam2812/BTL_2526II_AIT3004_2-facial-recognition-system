# CI/CD Pipeline

Cap nhat: `2026-05-11`.

## Tong quan

Moi khi push code len `main` hoac tao Pull Request vao `main`, GitHub Actions se:

1. Chay backend tests bang `pytest`
2. Chay `npm run lint` va `npm run build` cho frontend
3. Validate Docker Compose cho:
   - default stack
   - public tunnel stack qua `docker-compose.tunnel.yml`
4. Build du 3 Docker images: backend, worker, frontend
5. Push images len Docker Hub chi khi push truc tiep vao `main`
6. Smoke-test lai dung duong nop bai tren runner sach bang `docker compose pull` va `docker compose up -d`

## Luong hoat dong

```text
Push/PR vao main
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
       -> build backend/worker/frontend images
       -> push len Docker Hub neu day la push vao main
  -> dockerhub-smoke (chi khi push vao main)
       -> docker compose pull
       -> docker compose up -d
       -> health/login/settings OK
       -> direct backend /attendance/frame khong co token => 401
       -> frontend proxy /attendance/frame van goi duoc kiosk flow
```

## GitHub Secrets

De push image len Docker Hub, repo can:

| Secret Name | Gia tri |
| --- | --- |
| `DOCKERHUB_USERNAME` | `tlam281206` |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

## File lien quan

| File | Mo ta |
| --- | --- |
| `.github/workflows/ci.yml` | Workflow GitHub Actions |
| `docker-compose.yml` | Base stack |
| `docker-compose.tunnel.yml` | Public demo tunnel override |
| `docker-compose.build.yml` | Source-backed build override |
