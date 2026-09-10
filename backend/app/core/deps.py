# -*- coding: utf-8 -*-
"""请求级依赖：会话校验与 RBAC（docs/02 ADR-004、docs/03 5.1）"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.core.database import get_db
from app.core.response import BizError
from app.core.security import decode_token
from app.models.user import SysUser, SysSession


def _unauthorized() -> BizError:
    return BizError(10403, "会话已失效，请重新登录", http_status=401)


def get_current_user(request: Request, db: DbSession = Depends(get_db)) -> SysUser:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise _unauthorized()
    token = auth[7:]
    try:
        payload = decode_token(token)
    except Exception:
        raise _unauthorized()
    jti = payload.get("jti")
    user_id = int(payload.get("sub", "0"))
    sess = db.query(SysSession).filter(SysSession.jti == jti).first()
    from datetime import datetime, timezone
    if sess is None or sess.revoked_at is not None:
        raise _unauthorized()
    if sess.expires_at.tzinfo is not None:
        expired = sess.expires_at < datetime.now(timezone.utc)
    else:
        expired = sess.expires_at < datetime.utcnow()
    if expired:
        raise _unauthorized()
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if user is None or user.status != "enabled":
        raise _unauthorized()
    request.state.user = user
    return user


def require_roles(*roles: str):
    def checker(user: SysUser = Depends(get_current_user)) -> SysUser:
        if user.role not in roles:
            raise BizError(10404, "无权限执行该操作", http_status=403)
        return user
    return checker


require_maintainer = require_roles("maintainer", "admin")
require_admin = require_roles("admin")
