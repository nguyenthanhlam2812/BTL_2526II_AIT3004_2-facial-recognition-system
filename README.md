# AI Facial Recognition Attendance

## Muc tieu

Day la MVP cho bai toan check-in/check-out nhan vien bang nhan dien khuon mat.
Huong di cua repo:

- admin dang nhap va CRUD nhan vien
- upload anh enrollment
- worker tao embedding nen
- kiosk gui frame de recognition
- luu attendance event

## Trang thai hien tai

Da hoan thanh:

- schema MySQL va migration dau tien
- auth admin bang JWT
- employee CRUD API
- PoC recognition va threshold tai `recognition/`

Chua lam xong:

- enrollment flow that
- attendance recognition API that
- worker embedding + Qdrant/MinIO end-to-end
- frontend admin/kiosk
- nginx cho full stack

## Cau truc repo hien tai

```text
.
├── backend/          # FastAPI app
├── worker/           # worker cho background jobs
├── recognition/      # PoC va logic AI dung chung
├── scripts/
│   ├── poc/          # entrypoint chay PoC
│   └── seed/         # seed admin
├── docs/             # tai lieu ky thuat dang dung
├── data/demo/        # du lieu demo cho PoC
├── requirements/     # dependency theo vai tro
├── docker-compose.yml
├── alembic.ini
└── README.md
```

## Tai lieu can doc

- `docs/project-scope.md`: pham vi MVP
- `docs/architecture.md`: kien truc va luong chinh
- `docs/api-contract.md`: contract API de bam vao khi code
- `docs/database-setup.md`: setup MySQL local va migration
- `docs/demo-data.md`: snapshot du lieu PoC va threshold
- `docs/diagrams.md`: mermaid diagrams va ERD

## Chay backend local

### 1. Tao env

```powershell
Copy-Item .env.example .env
```

Neu MySQL local cua ban khong dung port mac dinh `3306`, sua lai `MYSQL_PORT` trong `.env`.

### 2. Cai dependency

```powershell
.venv\Scripts\pip install -r requirements\backend.txt
```

### 3. Chay migration

```powershell
.venv\Scripts\alembic upgrade head
```

### 4. Seed tai khoan admin

```powershell
.venv\Scripts\python scripts\seed\seed_admin.py
```

Tai khoan mac dinh:

- username: `admin`
- password: `admin123`

### 5. Chay API

```powershell
.venv\Scripts\python -m uvicorn backend.app.main:app --reload
```

Swagger:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API hien da chay

- `GET /healthz`
- `POST /api/auth/login`
- `GET /api/employees`
- `POST /api/employees`
- `PUT /api/employees/{employee_id}`
- `DELETE /api/employees/{employee_id}`

## Docker hien tai

`docker-compose.yml` hien dang bam vao cac service sau:

- `mysql`
- `redis`
- `minio`
- `qdrant`
- `backend`
- `worker`

Frontend va nginx se duoc them vao repo khi bat dau lam den phase do.

## Thu tu lam tiep

1. Khoa employee CRUD va commit moc nay
2. Lam enrollment API
3. Noi worker + MinIO + Qdrant
4. Lam attendance recognition API
5. Luc do moi mo rong frontend va full Docker stack
