# -*- coding: utf-8 -*-
"""用户管理接口（docs/05 4.1.4~4.1.7，仅 admin）"""
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.response import BizError, ok
from app.core.security import generate_random_password, hash_password, verify_password
from app.models.user import SysSession, SysUser
from app.services.audit_service import record

router = APIRouter(tags=["users"])


class UserCreateBody(BaseModel):
    username: str = Field(min_length=4, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=64)
    role: str = Field(pattern=r"^(user|maintainer|admin)$")


class UserUpdateBody(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    role: str | None = Field(default=None, pattern=r"^(user|maintainer|admin)$")
    status: str | None = Field(default=None, pattern=r"^(enabled|disabled)$")
    version: int


def _user_view(u: SysUser) -> dict:
    return {
        "id": u.id, "username": u.username, "display_name": u.display_name,
        "role": u.role, "status": u.status, "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "version": u.version,
    }


def _revoke_user_sessions(db: DbSession, user_id: int) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for sess in db.query(SysSession).filter(SysSession.user_id == user_id, SysSession.revoked_at.is_(None)).all():
        sess.revoked_at = now


@router.get("/users")
def list_users(
    keyword: str | None = None, role: str | None = None, status: str | None = None,
    page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100),
    user: SysUser = Depends(require_admin), db: DbSession = Depends(get_db),
):
    q = db.query(SysUser)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter((SysUser.username.like(like)) | (SysUser.display_name.like(like)))
    if role:
        q = q.filter(SysUser.role == role)
    if status:
        q = q.filter(SysUser.status == status)
    total = q.count()
    items = (q.order_by(SysUser.id.desc()).offset((page - 1) * pageSize).limit(pageSize).all())
    return ok({"total": total, "page": page, "pageSize": pageSize, "items": [_user_view(u) for u in items]})


@router.post("/users")
def create_user(body: UserCreateBody, request: Request,
                admin: SysUser = Depends(require_admin), db: DbSession = Depends(get_db)):
    if db.query(SysUser).filter(SysUser.username == body.username).first():
        raise BizError(10502, "账号已存在")
    initial = generate_random_password(10)
    u = SysUser(username=body.username, display_name=body.display_name, role=body.role,
                password_hash=hash_password(initial), status="enabled", created_by=admin.id)
    db.add(u)
    db.flush()
    record(db, "USER_CREATE", actor=admin, object_type="user", object_id=u.id,
           summary=f"创建用户 {body.username}（角色 {body.role}）",
           ip=request.client.host if request.client else None)
    db.commit()
    return ok({"id": u.id, "initial_password": initial})


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserUpdateBody, request: Request,
                admin: SysUser = Depends(require_admin), db: DbSession = Depends(get_db)):
    u = db.query(SysUser).filter(SysUser.id == user_id).first()
    if u is None:
        raise BizError(10501, "用户不存在", http_status=404)
    if u.version != body.version:
        raise BizError(10504, "版本冲突，请刷新重试", http_status=409)
    changes = []
    if body.display_name is not None and body.display_name != u.display_name:
        u.display_name = body.display_name
        changes.append("姓名")
    if body.role is not None and body.role != u.role:
        u.role = body.role
        changes.append(f"角色→{body.role}")
    if body.status is not None and body.status != u.status:
        if body.status == "disabled":
            if u.id == admin.id:
                raise BizError(10503, "不允许停用自己")
            if (db.query(SysUser).filter(SysUser.role == "admin", SysUser.status == "enabled").count() <= 1
                    and u.role == "admin"):
                raise BizError(10503, "不允许停用最后一个管理员")
            _revoke_user_sessions(db, u.id)
        u.status = body.status
        changes.append(f"状态→{body.status}")
    u.updated_by = admin.id
    u.version += 1
    record(db, "USER_DISABLE" if body.status == "disabled" else "USER_UPDATE",
           actor=admin, object_type="user", object_id=u.id,
           summary=f"编辑用户 {u.username}: {'、'.join(changes) or '无变更'}",
           ip=request.client.host if request.client else None)
    db.commit()
    return ok(_user_view(u))


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, request: Request,
                   admin: SysUser = Depends(require_admin), db: DbSession = Depends(get_db)):
    u = db.query(SysUser).filter(SysUser.id == user_id).first()
    if u is None:
        raise BizError(10501, "用户不存在", http_status=404)
    new_pwd = generate_random_password(10)
    u.password_hash = hash_password(new_pwd)
    _revoke_user_sessions(db, u.id)
    u.version += 1
    record(db, "USER_RESET", actor=admin, object_type="user", object_id=u.id,
           summary=f"重置用户 {u.username} 密码（全部会话已撤销）",
           ip=request.client.host if request.client else None)
    db.commit()
    return ok({"new_password": new_pwd})
