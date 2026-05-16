# Cloudflare Tunnel

## Tổng quan

Cloudflare Tunnel cho phép mở stack Docker local ra Internet qua HTTPS để demo từ xa.
Quick Tunnel chỉ phù hợp cho demo có kiểm soát, không phải môi trường production.

## Secret bắt buộc trước khi bật tunnel

Public demo path vẫn được hỗ trợ, nhưng phải fail-safe qua `PUBLIC_DEMO_MODE=true`.
Khi mode này bật, backend sẽ từ chối startup nếu vẫn dùng:

- `SEED_ADMIN_PASSWORD=admin123`
- `JWT_SECRET_KEY=change-me`
- `KIOSK_API_TOKEN=local-kiosk-token`

Tạo hoặc sửa `.env.docker`:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=replace-with-a-strong-demo-password
KIOSK_API_TOKEN=replace-with-a-strong-kiosk-token
```

Checklist nhanh:

1. `docker compose up -d` đã chạy ổn local stack
2. `.env.docker` đã có `JWT_SECRET_KEY` mới
3. `.env.docker` đã có `SEED_ADMIN_PASSWORD` mới
4. `.env.docker` đã có `KIOSK_API_TOKEN` mới
5. Chỉ sau đó mới bật compose override cho tunnel

## Lệnh chạy đúng

Chạy full stack local:

```bash
docker compose up -d
```

Bật tunnel bằng compose override:

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel up -d
```

Nếu cần smoke-test từ mã nguồn local rồi mới mở tunnel:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml -f docker-compose.tunnel.yml --profile tunnel up -d --build backend worker frontend tunnel
```

## Lấy URL public

```bash
docker compose logs tunnel
```

Tìm URL dạng:

```text
https://random-name.trycloudflare.com
```

Sử dụng:

- Admin: `https://random-name.trycloudflare.com/login`
- Kiosk: `https://random-name.trycloudflare.com/kiosk`

## Tắt tunnel

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel stop tunnel
```

Tắt cả stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel down
```

## Lưu ý security

- Public demo mode không dựa vào `Host` header để chặn credential mặc định.
- Security gate nằm ở startup config: default admin password, default JWT secret và default kiosk token đều bị từ chối khi `PUBLIC_DEMO_MODE=true`.
- Kiosk page vẫn public, nhưng `POST /api/attendance/frame` chỉ đi qua được khi có `X-Kiosk-Token`. Frontend/Nginx inject token này server-side cho flow `/kiosk`.
- Endpoint kiosk đã có rate limit; phần còn thiếu nếu muốn production-grade là device provisioning, audit và giám sát dài hạn.

## File liên quan

- `docker-compose.yml`: base stack
- `docker-compose.tunnel.yml`: bật `PUBLIC_DEMO_MODE=true` cho backend
- `.env.docker`: secret thực tế cho public demo
- `.env.docker.example`: mẫu env
