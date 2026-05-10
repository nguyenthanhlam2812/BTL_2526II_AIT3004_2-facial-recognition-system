# Cloudflare Tunnel – Triển khai hệ thống lên Internet

Cập nhật: `2026-05-10`.

## Tổng quan

**Cloudflare Tunnel** cho phép expose hệ thống chạy trên máy local (Docker) ra Internet qua HTTPS mà **không cần**:
- Mua domain.
- Mở port trên router/firewall.
- Cấu hình SSL/TLS thủ công.

Rất phù hợp để **demo project** cho giảng viên hoặc bạn bè truy cập từ xa qua điện thoại/laptop.

## Sơ đồ luồng hoạt động

```
Người dùng bên ngoài (điện thoại/laptop)
  │
  │  Truy cập URL: https://xxxxx.trycloudflare.com
  ▼
Cloudflare Edge Network (HTTPS / SSL termination miễn phí)
  │
  │  Tunnel mã hoá
  ▼
Container cloudflared (trong Docker Compose trên máy bạn)
  │
  │  Forward HTTP request
  ▼
Container frontend (Nginx – port 80)
  ├─ Serve giao diện React (SPA)
  └─ Proxy /api/* → Container backend (FastAPI – port 8000)
                         └─ Truy vấn MySQL, Redis, Qdrant, MinIO
```

## Cách sử dụng

### Bước 1: Bật tunnel

Chạy lệnh sau (đảm bảo các service khác đã chạy):

```bash
# Bật tất cả service + tunnel
docker compose --profile tunnel up -d

# Hoặc nếu các service khác đã chạy rồi, chỉ bật thêm tunnel
docker compose --profile tunnel up -d tunnel
```

### Bước 2: Lấy URL công khai

```bash
docker compose logs tunnel
```

Tìm dòng có chứa URL dạng:

```
INF | https://random-name-here.trycloudflare.com
```

Copy URL đó và chia sẻ cho người khác truy cập.

### Bước 3: Truy cập từ bên ngoài

- Mở URL trên trình duyệt bất kỳ → thấy trang Login.
- Đăng nhập bằng tài khoản admin (`admin` / `admin123`).
- Mở trang Kiosk: thêm `/kiosk` vào cuối URL.
- Camera hoạt động bình thường qua HTTPS (trình duyệt yêu cầu HTTPS để dùng webcam).

### Tắt tunnel

```bash
docker compose --profile tunnel stop tunnel
```

Hoặc tắt toàn bộ:

```bash
docker compose --profile tunnel down
```

## Lưu ý quan trọng

| Đặc điểm | Chi tiết |
|---|---|
| **Loại tunnel** | Quick Tunnel (không cần tài khoản Cloudflare) |
| **URL** | Thay đổi mỗi lần restart container tunnel |
| **HTTPS** | Tự động, miễn phí, do Cloudflare cấp |
| **Hiệu năng** | Đủ tốt cho demo, không khuyến khích dùng cho production |
| **Profile** | Tunnel chỉ chạy khi dùng `--profile tunnel`, không ảnh hưởng lệnh `docker compose up` bình thường |

## Tại sao chọn Cloudflare Tunnel?

| Tiêu chí | Cloudflare Tunnel | Ngrok | Port Forwarding |
|---|---|---|---|
| Miễn phí | ✅ | ✅ (giới hạn) | ✅ |
| HTTPS tự động | ✅ | ✅ | ❌ |
| Không cần mở port router | ✅ | ✅ | ❌ |
| Không cần đăng ký tài khoản | ✅ (Quick Tunnel) | ❌ | ✅ |
| Tốc độ | Nhanh (CDN toàn cầu) | Trung bình | Phụ thuộc mạng |

## File liên quan

| File | Mô tả |
|---|---|
| `docker-compose.yml` | Service `tunnel` với profile `tunnel` |
