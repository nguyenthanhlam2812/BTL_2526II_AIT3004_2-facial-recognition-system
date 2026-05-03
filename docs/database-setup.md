# Thiet lap Database Local

Tai lieu nay chot cach lam hien tai: phat trien voi **MySQL local** truoc, sau do moi doi sang Docker khi can dong goi full stack.

## Tool dang dung

- MySQL Workbench: tao database, user, kiem tra bang
- PowerShell: chay lenh trong project
- SQLAlchemy: dinh nghia schema bang model Python
- Alembic: sinh va chay migration

## File env lien quan

- `.env`: cau hinh local hien tai
- `.env.example`: mau local cho may khac
- `.env.docker`: cau hinh khi chay trong Docker
- `.env.docker.example`: mau Docker

Quy uoc:

- chay local: dung `.env`
- chay Docker: dung `.env.docker`

## 1. Tao database

Trong MySQL Workbench, chay:

```sql
CREATE DATABASE IF NOT EXISTS face_attendance
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

## 2. Tao user ung dung

```sql
CREATE USER IF NOT EXISTS 'app'@'localhost' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'app'@'localhost';

CREATE USER IF NOT EXISTS 'app'@'127.0.0.1' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON face_attendance.* TO 'app'@'127.0.0.1';

FLUSH PRIVILEGES;
```

## 3. Kiem tra `.env`

Toi thieu can dung cac bien sau:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=face_attendance
MYSQL_USER=app
MYSQL_PASSWORD=app_password
```

Neu MySQL local cua ban dang chay port khac, sua `MYSQL_PORT` cho dung voi may.

## 4. Cai dependency backend

```powershell
.venv\Scripts\pip install -r requirements\backend.txt
```

## 5. Chay migration

```powershell
.venv\Scripts\alembic upgrade head
```

## 6. Kiem tra ket noi nhanh

```powershell
.venv\Scripts\python -c "from sqlalchemy import text; from backend.app.db.session import engine; conn = engine.connect(); print(conn.execute(text('SELECT 1')).scalar()); conn.close()"
```

Neu in ra `1` la ket noi DB on.

## Ghi chu

- Khong tao bang bang tay roi bo qua migration
- Khong hard-code host/port DB trong code
- Khong dung root cho app logic
- Chot schema qua model + Alembic de sau nay doi sang Docker khong bi roi
