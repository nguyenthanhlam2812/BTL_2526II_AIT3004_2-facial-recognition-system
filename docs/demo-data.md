# Demo Data Checklist

## Mục đích

Tài liệu này dùng để chuẩn bị dữ liệu demo và kiểm soát consent trước khi bước sang Phase 2.

## Mục tiêu dữ liệu tối thiểu

- 5-10 nhân viên demo.
- 3-5 ảnh đăng ký cho mỗi nhân viên.
- 1 bộ ảnh hoặc video của người lạ để test `unknown`.
- 1 tài khoản admin demo.

## Checklist chất lượng ảnh

- Ảnh rõ mặt, không bị blur nặng.
- Ánh sáng đủ, không quá tối.
- Ưu tiên góc chính diện.
- Không đeo khẩu trang trong ảnh đăng ký.
- Khuôn mặt chiếm phần đủ lớn trong ảnh.

## Checklist consent

- Người trong ảnh đồng ý cho dùng vào mục đích demo học phần.
- Ảnh không lấy từ nguồn không rõ ràng.
- Không dùng dữ liệu nhạy cảm ngoài phạm vi đồ án.
- Có thể xóa dữ liệu demo sau khi kết thúc học phần nếu cần.

## Quy ước tổ chức dữ liệu

- Mỗi nhân viên có 1 thư mục riêng.
- Tên file nên theo mẫu: `employee_code_full_name_01.jpg`
- Tách riêng thư mục `unknown/` cho dữ liệu người lạ.

Ví dụ:

```text
data/demo/
  enrolled/
    employee_001/
      employee_001_01.jpg
      employee_001_02.jpg
      employee_001_03.jpg
  unknown/
    visitor_01.jpg
```

## Snapshot Phase 2 hiện tại

Cập nhật lần cuối: `2026-04-23`

- Tổng ảnh đang dùng cho PoC: `13`
- Enrolled identities: `2`
- Ảnh enrolled:
  - `lam`: `5` ảnh
  - `nu`: `3` ảnh
- Ảnh unknown: `5`
- Kết quả detect:
  - `13` ảnh `ok`
  - `0` ảnh `multiple_faces_detected`

## Kết quả threshold sơ bộ

Nguồn kết quả: `artifacts/poc/cosine_similarity.json`

- `positive_pairs`: `13`
- `negative_pairs`: `55`
- `positive min`: `0.362113`
- `negative max`: `0.150669`
- `recommended_threshold`: `0.256391`
- `separation_gap`: `0.211444`

## Quyết định tạm thời cho Phase 3

- Dùng `0.26` làm threshold cấu hình ban đầu cho luồng attendance.
- Threshold này chỉ là giá trị PoC, vẫn phải rerun khi bộ ảnh consent lớn hơn.
- Bộ dữ liệu PoC hiện tại đã clean, tất cả ảnh đang dùng đều detect `1` khuôn mặt.

## Trạng thái cần chốt trước Phase 2

- Danh sách nhân viên demo đã đủ.
- Ảnh đăng ký đạt chất lượng tối thiểu.
- Consent đã được xác nhận.
- Có ít nhất 1 case người lạ để test deny.
