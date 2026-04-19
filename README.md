

## Current Focus

- Chot PoC detect + embedding bang `InsightFace + OpenCV`
- Dung du lieu demo local de kiem tra enrolled vs unknown
- Giu logic AI tach khoi script thu nghiem de sang Phase 3 co the dua vao backend va worker

## Next Phases

- `frontend/`, `backend/`, `worker/`, `nginx/`, `tests/` se duoc them sau khi bat dau Phase 3.
- Hien tai chua tao placeholder rong cho cac phan nay de repo chi phan anh nhung gi da lam xong.

## Clean Scope

- Da bo cac file noi bo chi phuc vu checkpoint va phan cong nhom.
- Repo hien giu lai cac file can cho proposal, kien truc, PoC va huong di tiep theo.

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
