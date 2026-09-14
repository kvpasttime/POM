# POM — 历史采购报价查询系统

把分散在几十份 Excel 里的采购需求与供应商报价，整理成**可检索、可追溯**的结构化报价库。

- 每条报价都能回到**原始文件、工作表、行号、单元格原文**
- 兼容乱表：标准模板自动识别 + 表头错位自动对齐 + 人工字段映射兜底
- 横向多供应商报价自动拆分为多条记录
- 价格、含税、含运、渠道从备注中提取，低可信结果标记"待核对"，原文永不覆盖

> 纯查询/资料库定位，**不做**审批、库存、财务等 ERP 流程。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Element Plus + Vite |
| 后端 | Python + FastAPI + SQLAlchemy 2 |
| 数据库 | PostgreSQL（生产）/ SQLite（开发） |
| Excel 解析 | xlrd（.xls）+ openpyxl（.xlsx） |
| 部署 | Docker Compose（nginx + backend + postgres + backup-cron） |

## 功能

- **账号与权限**：三类角色（查询 / 维护 / 管理），不开放注册，登录限速，会话即时撤销
- **Excel 导入**：批量上传、签名校验、工作表/表头识别、列位移检测、字段映射模板、行级预览校验、文件级/行级/业务疑似三级查重、批次报告、失败整批回滚
- **搜索与追溯**：关键词+组合筛选+排序分页；详情含原始文本、来源定位、兄弟报价；原文件鉴权下载
- **数据维护**：字段纠错（前后值+原因留痕）、软删除/恢复、质量状态标记
- **系统管理**：审计日志（含敏感字段查看审计）、备份状态

## 快速开始（一键脚本）

Windows 下双击仓库根目录：

- **`start.bat`** — 自动检查并创建 venv / 安装依赖 / 种子管理员，然后开两个窗口分别启动后端(:8000)与前端(:5173)，并打开浏览器。（首次运行约需 2 分钟装依赖；首次创建库时会打印 admin 初始密码，仅显示一次，登录后请修改）
- **`stop.bat`** — 按端口停止前后端服务。

手动方式见下。

## 手动启动（本地开发）

### 后端

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Windows
# source .venv/bin/activate && pip install -r requirements.txt

python -m app.seed          # 首次：建表 + 生成管理员（随机密码仅打印一次）
python -m uvicorn app.main:app --port 8000
```

默认使用 SQLite（`./pom.db`）。要连 PostgreSQL：

```bash
set DATABASE_URL=postgresql://pom:PASSWORD@localhost:5432/pom
```

API 文档：<http://localhost:8000/docs>

### 前端

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173（已代理 /api → 8000）
```

### 测试

```bash
cd backend
python -m pytest tests/ -q
```

测试包含认证/权限/会话失效、导入引擎单测与**全链路冒烟**。历史样例回归测试（`test_samples_regression.py`）在 `fixtures/` 存在样例文件时自动启用——真实业务样例不入 git。

## 生产部署（Docker Compose）

```bash
cd deploy
cp .env.example .env          # 修改 SECRET_KEY 与 POSTGRES_PASSWORD
docker compose up -d --build
```

- 建议前置 HTTPS（云 LB / 反向代理证书），应用不写死域名
- 数据库端口不对公网映射；上传目录不可执行
- 备份：`backup` 服务每日执行，库 + 原始文件同一产物；恢复见 [deploy/backup/RESTORE.md](deploy/backup/RESTORE.md)
- 首次启动进入容器执行 `python -m app.seed` 生成管理员

## 目录结构

```
├── docs/        # 设计文档（版本规划/架构/功能/UI/API/DB/任务清单/验收）
├── backend/     # FastAPI 后端（含导入引擎 importers/ 与测试）
├── frontend/    # Vue3 前端
├── deploy/      # Compose/Nginx/备份/恢复
└── fixtures/    # （gitignore）真实样例 Excel，仅本地回归用
```

## 设计文档

| 文档 | 内容 |
| --- | --- |
| [01-版本规划](docs/01-版本规划.md) | V1.0 MVP 范围与路线 |
| [02-架构设计](docs/02-架构设计.md) | 边界、ADR、部署视图 |
| [03-功能详细设计](docs/03-功能详细设计.md) | 规则/状态/权限/验收 |
| [04-前端UI设计](docs/04-前端UI设计/00-主控文档.md) | 页面级详设 |
| [05-API接口设计](docs/05-API接口设计.md) | 接口契约 |
| [06-数据库设计](docs/06-数据库设计.md) | 表结构与约束 |
| [08-研发任务清单](docs/08-研发任务清单.md) | 可执行任务分解 |

## 安全说明

- 密码 PBKDF2-SHA256（600k 迭代）哈希存储，初始密码随机生成仅显示一次
- 电话/地址/银行账户等敏感字段按角色脱敏，查看明文写入审计
- 上传校验扩展名+文件签名，随机文件名隔离存储
- 认证后接口响应 `Cache-Control: no-store`，禁 CDN 缓存

## License

[MIT](LICENSE)
