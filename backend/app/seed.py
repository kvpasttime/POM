# -*- coding: utf-8 -*-
"""种子管理员：首个 admin（无默认密码，随机生成输出一次，R-AUTH-05）"""
import sys

from app.core.database import SessionLocal, Base, engine
import app.models.user  # noqa: F401  注册全部模型后再建表
import app.models.business  # noqa: F401
import app.models.ops  # noqa: F401
from app.core.security import hash_password, generate_random_password
from app.models.user import SysUser


def seed() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(SysUser).count() > 0:
            print("users exist, skip seeding")
            return
        password = generate_random_password(12)
        admin = SysUser(
            username="admin",
            password_hash=hash_password(password),
            display_name="系统管理员",
            role="admin",
            status="enabled",
        )
        db.add(admin)
        db.commit()
        print("=" * 60)
        print("初始管理员账号: admin")
        print(f"初始密码（仅显示一次，请立即修改）: {password}")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(seed())
