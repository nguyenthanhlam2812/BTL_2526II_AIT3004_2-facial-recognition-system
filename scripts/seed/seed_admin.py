from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.models.user import USER_ROLE_OWNER, User
from backend.app.security import get_password_hash
from backend.app.config import get_settings


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        existing = db.scalar(
            select(User).where(User.username == settings.seed_admin_username)
        )
        if existing is not None:
            print("Admin user already exists.")
            return

        admin = User(
            username=settings.seed_admin_username,
            password_hash=get_password_hash(settings.seed_admin_password),
            role=USER_ROLE_OWNER,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Seeded admin user: {settings.seed_admin_username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
