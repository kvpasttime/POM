# -*- coding: utf-8 -*-
"""文件存储服务（M-006）：隔离保存、规范化命名（R-IMP-01/02、PRD 8.2）"""
import os
import re
import secrets
from datetime import datetime

from app.core.config import get_settings

_NAME_SAFE = re.compile(r"[^0-9A-Za-z.\u4e00-\u9fff_-]+")


def safe_original_name(name: str) -> str:
    """规范化原始文件名（仅展示用，不参与路径）"""
    base = os.path.basename(name or "file")
    cleaned = _NAME_SAFE.sub("_", base).strip("._") or "file"
    return cleaned[:200]


def save_upload(data: bytes, original_name: str) -> str:
    """保存到 日期目录/随机名.ext，返回相对路径。随机名杜绝路径穿越与执行。"""
    settings = get_settings()
    ext = os.path.splitext(original_name.lower())[1][:8]
    day = datetime.now().strftime("%Y%m%d")
    dirpath = os.path.join(settings.upload_dir, day)
    os.makedirs(dirpath, exist_ok=True)
    stored = f"{secrets.token_hex(16)}{ext}"
    full = os.path.join(dirpath, stored)
    with open(full, "wb") as fh:
        fh.write(data)
    return os.path.join(day, stored)


def resolve_path(relative: str) -> str:
    """把存储相对路径解析为绝对路径（拒绝越界）"""
    settings = get_settings()
    base = os.path.abspath(settings.upload_dir)
    full = os.path.abspath(os.path.join(base, relative))
    if not full.startswith(base):
        raise ValueError("非法路径")
    return full
