

## Quickstart

1. Tao virtualenv:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Cai dependencies cho PoC:

```powershell
pip install -r requirements/poc.txt
```

3. Dat anh demo vao `data/demo/`.
Xem quy uoc va cau truc mau tai `docs/demo-data.md`.

4. Chay PoC:

```powershell
python scripts/poc/face_detect_embed.py --input data/demo --output artifacts/poc/results.json --annotated-dir artifacts/poc/annotated
```

5. Danh gia cosine similarity va threshold so bo:

```powershell
python scripts/poc/cosine_similarity_eval.py --input data/demo --output artifacts/poc/cosine_similarity.json
```

## Notes

- Anh demo local trong `data/demo/` dang duoc ignore de tranh commit du lieu ca nhan.
- `artifacts/` chi la output local, khong commit.
- Lan chay dau tien co the can model weights cua InsightFace.
- Neu muon tro local model weights, dung them `--model-root <path>`.
