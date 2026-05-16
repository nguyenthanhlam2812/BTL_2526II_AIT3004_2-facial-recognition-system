# Dữ liệu demo

Tài liệu này mô tả bộ dữ liệu tối thiểu để chạy enrollment và demo chấm công.

## Nguyên tắc

- Không commit dataset lớn vào repo.
- Không dùng ảnh không rõ nguồn.
- Không dùng ảnh khi chưa có đồng ý.

## Bộ demo tối thiểu

- 3-5 nhân viên demo.
- 3-5 ảnh enrollment cho mỗi nhân viên.
- 1-3 ảnh/frame người lạ để test `unknown_face`.
- 1 ảnh nhiều khuôn mặt để test `multiple_faces` nếu có.
- Tài khoản admin: `admin` / `admin123`.

## Chất lượng ảnh

- Rõ mặt, không blur nặng.
- Đủ sáng.
- Ưu tiên góc chính diện.
- Mỗi ảnh enrollment chỉ có 1 khuôn mặt.
- Không đeo khẩu trang trong ảnh enrollment.

## Đồng ý sử dụng ảnh

- Người trong ảnh đồng ý dùng cho demo học phần.
- Ảnh không chứa dữ liệu nhạy cảm ngoài phạm vi đồ án.
- Có thể xóa dữ liệu demo sau khi kết thúc học phần.

## Tổ chức thư mục

```text
data/demo/
  enrolled/
    E001_nguyen_van_a/
      E001_nguyen_van_a_01.jpg
      E001_nguyen_van_a_02.jpg
      E001_nguyen_van_a_03.jpg
  unknown/
    visitor_01.jpg
  multiple_faces/
    group_01.jpg
```

## Ngưỡng nhận diện

Backend hiện dùng:

```env
ATTENDANCE_THRESHOLD=0.3
```

Nếu bộ ảnh demo thực tế khác nhiều về ánh sáng hoặc góc mặt, có thể điều chỉnh threshold trong `.env.docker` hoặc qua trang `Cấu hình`.
