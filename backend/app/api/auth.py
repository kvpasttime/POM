# -*- coding: utf-8 -*-
"""认证接口（docs/05 4.1.1~4.1.3）"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.response import BizError, ok
from app.core.ratelimit import limiter
from app.core.security import (
    create_token, decode_token, new_jti, session_expiry, verify_password,
)
from app.models.user import SysSession, SysUser
from app.services.audit_service import record

router = APIRouter(tags=["auth"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _revoke(db: DbSession, jti: str | None = None, user_id: int | None = None) -> None:
    now = datetime.now(timezone.utc)
    q = db.query(SysSession)
    if jti:
        q = q.filter(SysSession.jti == jti)
    if user_id:
        q = q.filter(SysSession.user_id == user_id)
    for sess in q.all():
        if sess.revoked_at is None:
            sess.revoked_at = now


@router.post("/auth/login")
def login(body: LoginBody, request: Request, db: DbSession = Depends(get_db)):
    ip = _client_ip(request)
    # IP 级限速
    if not limiter.check_ip(ip):
        raise BizError(10402, "尝试过于频繁，请稍后再试", http_status=429)
    # 账号锁定（R-AUTH-11/12）
    remain = limiter.is_locked(body.username)
    if remain > 0:
        raise BizError(10402, f"失败次数过多，已临时锁定，请 {remain // 60 + 1} 分钟后再试",
                       http_status=429, extra={"retry_after": remain})

    user = db.query(SysUser).filter(SysUser.username == body.username).first()
    def _fail(msg: str, code: int = 10401, status: int = 401):
        limiter.record_failure(body.username)
        record(db, "LOGIN_FAILED", actor=user, result="failed", summary=msg,
               detail={"ip": ip}, ip=ip)
        db.commit()
        raise BizError(code, msg, http_status=status)

    if user is None or not verify_password(body.password, user.password_hash):
        _fail("账号或密码错误")
    if user.status != "enabled":
        record(db, "LOGIN_FAILED", actor=user, result="failed", summary="账号已停用",
               detail={"ip": ip}, ip=ip)
        db.commit()
        raise BizError(10403, "账号已停用，请联系管理员", http_status=403)

    expires = session_expiry()
    jti = new_jti()
    token = create_token(user.id, jti, expires)
    sess = SysSession(user_id=user.id, jti=jti, expires_at=expires, ip=ip,
                      user_agent=(request.headers.get("user-agent") or "")[:256])
    db.add(sess)
    user.last_login_at = datetime.utcnow()
    limiter.reset(body.username)
    record(db, "LOGIN", actor=user, object_type="user", object_id=user.id,
           summary="登录成功", ip=ip)
    db.commit()
    return ok({
        "token": token,
        "expires_at": expires.isoformat(),
        "user": {"id": user.id, "username": user.username,
                 "display_name": user.display_name, "role": user.role},
    })


@router.post("/auth/logout")
def logout(request: Request, user: SysUser = Depends(get_current_user),
           db: DbSession = Depends(get_db)):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    try:
        payload = decode_token(token)
        _revoke(db, jti=payload.get("jti"))
    except Exception:
        pass
    record(db, "LOGOUT", actor=user, object_type="user", object_id=user.id, summary="退出登录")
    db.commit()
    return ok({"success": True})


@router.get("/auth/me")
def me(user: SysUser = Depends(get_current_user), db: DbSession = Depends(get_db)):
    auth = request_token_expiry(user, db)
    return ok({
        "id": user.id, "username": user.username, "display_name": user.display_name,
        "role": user.role, "session_expires_at": auth,
    })


def request_token_expiry(user: SysUser, db: DbSession) -> str | None:
    sess = (db.query(SysSession)
            .filter(SysSession.user_id == user.id, SysSession.revoked_at.is_(None))
            .order_by(SysSession.expires_at.desc()).first())
    return sess.expires_at.isoformat() if sess else None
