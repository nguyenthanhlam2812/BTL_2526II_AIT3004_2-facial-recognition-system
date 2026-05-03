# Recognition Models

Tai lieu nay ghi lai lua chon model hien tai cho recognition trong MVP.

## Lua chon hien tai

- Detection va embedding dang dung `InsightFace`
- Model pack hien tai: `buffalo_l`
- Moi truong uu tien: CPU-first de demo on dinh

## Ly do chon

- De dung trong PoC va backend integration
- Du tot cho bo du lieu demo hien tai
- Giu MVP gon, khong om them nhieu lop abstraction som

## Trang thai trong repo

- PoC detect + embedding: `recognition/pipelines/face_detect_embed.py`
- Threshold eval: `recognition/pipelines/cosine_similarity_eval.py`

## Huong refactor sau

Khi bat dau noi flow attendance that, co the tach nho thanh:

- `detect.py`
- `align.py`
- `embed.py`
- `similarity.py`
- `threshold.py`

Hien tai chua uu tien tach nho vi backend core va attendance flow con quan trong hon.
