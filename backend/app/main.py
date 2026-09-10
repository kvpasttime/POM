# -*- coding: utf-8 -*-
"""POM FastAPI 应用入口（M00-OPS-001）"""
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.response import BizError, biz_error_handler

class _RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
)
for _h in logging.root.handlers:
    _h.addFilter(_RequestIdFilter())


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name, version=get_settings().version)
    app.add_exception_handler(BizError, biz_error_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        response = await call_next(request)
        # 认证内容禁缓存（PRD 8.2 / docs/05 2.2）
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Request-Id"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        logging.getLogger("pom").exception("unhandled error: %s", exc)
        return JSONResponse(
            {"code": 50000, "message": "服务器内部错误，请联系管理员", "data": None},
            status_code=500,
        )

    from app.api import auth, users, quotes, imports, maintenance, admin
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(quotes.router, prefix="/api/v1")
    app.include_router(imports.router, prefix="/api/v1")
    app.include_router(maintenance.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")

    @app.get("/api/v1/health")
    def health():
        return {"code": 0, "message": "ok", "data": {"status": "up", "version": get_settings().version}}

    return app


app = create_app()
