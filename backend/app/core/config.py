# -*- coding: utf-8 -*-
"""应用配置（环境变量驱动，见 docs/02 8.3 与 deploy/.env.example）"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "POM 历史采购报价查询系统"
    version: str = "1.0.0"
    # SQLite 开发 / PostgreSQL 生产（ADR-005）
    database_url: str = "sqlite:///./pom.db"
    # JWT 签名密钥（生产必须由 .env 提供）
    secret_key: str = "dev-only-secret-key-change-me-in-production"
    jwt_algorithm: str = "HS256"
    session_ttl_hours: int = 12
    # 登录限速（R-AUTH-11/12）
    login_max_failures: int = 5
    login_lock_minutes: int = 15
    login_ip_max_per_minute: int = 10
    # 上传限制（R-IMP-01）
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 20
    # 备份目录（backup-status 扫描）
    backup_dir: str = "./data/backups"
    # 数据
    default_page_size: int = 20
    max_page_size: int = 100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
