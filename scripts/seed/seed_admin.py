from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.security import get_password_hash


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.username == "admin"))
        if existing is not None:
            print("Admin user already exists.")
            return

        admin = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("Seeded admin user: admin / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
