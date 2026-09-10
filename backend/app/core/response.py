# -*- coding: utf-8 -*-
"""统一响应包裹与业务错误（docs/05 2.5）"""
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class BizError(Exception):
    """业务错误：code 为业务错误码，http_status 为 HTTP 状态"""

    def __init__(self, code: int, message: str, http_status: int = 400, extra: dict | None = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.extra = extra or {}
        super().__init__(message)


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


async def biz_error_handler(request: Request, exc: BizError):
    payload = {"code": exc.code, "message": exc.message, "data": exc.extra or None}
    resp = JSONResponse(payload, status_code=exc.http_status)
    resp.headers["Cache-Control"] = "no-store"
    return resp
