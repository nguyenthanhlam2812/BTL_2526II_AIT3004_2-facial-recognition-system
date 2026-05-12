# Cloudflare Tunnel

Cap nhat: `2026-05-11`.

## Tong quan

Cloudflare Tunnel cho phep expose stack Docker local ra Internet qua HTTPS de demo tu xa.
Quick Tunnel chi phu hop cho demo co kiem soat, khong phai production.

## Secret bat buoc truoc khi bat tunnel

Public demo path van duoc support, nhung no phai fail-safe qua `PUBLIC_DEMO_MODE=true`.
Khi mode nay bat, backend se tu choi startup neu van dung:

- `SEED_ADMIN_PASSWORD=admin123`
- `JWT_SECRET_KEY=change-me`
- `KIOSK_API_TOKEN=local-kiosk-token`

Tao hoac sua `.env.docker`:

```env
JWT_SECRET_KEY=replace-with-a-long-random-secret
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=replace-with-a-strong-demo-password
KIOSK_API_TOKEN=replace-with-a-strong-kiosk-token
```

Checklist nhanh:

1. `docker compose up -d` da chay on local stack
2. `.env.docker` da co `JWT_SECRET_KEY` moi
3. `.env.docker` da co `SEED_ADMIN_PASSWORD` moi
4. `.env.docker` da co `KIOSK_API_TOKEN` moi
5. Chi sau do moi bat compose override cho tunnel

## Lenh chay dung

Chay full stack local:

```bash
docker compose up -d
```

Bat tunnel bang compose override:

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel up -d
```

Neu can smoke-test source local roi moi mo tunnel:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml -f docker-compose.tunnel.yml --profile tunnel up -d --build backend worker frontend tunnel
```

## Lay URL public

```bash
docker compose logs tunnel
```

Tim URL dang:

```text
https://random-name.trycloudflare.com
```

Su dung:

- Admin: `https://random-name.trycloudflare.com/login`
- Kiosk: `https://random-name.trycloudflare.com/kiosk`

## Tat tunnel

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel stop tunnel
```

Tat ca stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.tunnel.yml --profile tunnel down
```

## Luu y security

- Public demo mode khong dua vao `Host` header de chan credential mac dinh.
- Security gate nam o startup config: default admin password, default JWT secret va default kiosk token deu bi tu choi khi `PUBLIC_DEMO_MODE=true`.
- Kiosk page van public, nhung `POST /api/attendance/frame` chi di qua duoc khi co `X-Kiosk-Token`. Frontend/Nginx inject token nay server-side cho flow `/kiosk`.
- Day van la controlled demo surface, khong phai hardening production-grade nhu device provisioning hay rate-limit.
- Attendance event hien chua luu snapshot audit vao MinIO; MinIO dang duoc dung cho enrollment images va demo assets.

## File lien quan

- `docker-compose.yml`: base stack
- `docker-compose.tunnel.yml`: bat `PUBLIC_DEMO_MODE=true` cho backend
- `.env.docker`: secret thuc te cho public demo
- `.env.docker.example`: mau env
