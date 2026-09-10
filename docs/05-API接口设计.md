---
doc_id: API-POM-V1.0
title: POM 历史采购报价查询系统 V1.0 API 接口设计
owner: POM 项目组
status: DRAFT
last_reviewed: 2026-09-09
source_of_truth: false
supersedes: []
related_docs:
  - docs/03-功能详细设计.md
  - docs/01-版本规划.md
  - docs/02-架构设计.md
  - docs/07-API和数据库任务清单.md
  - docs/06-数据库设计.md
related_code_paths:
  - backend/app/api
change_triggers:
  - 功能范围调整
  - 接口边界调整
  - 数据库与 API 承接边界调整
---

# POM 历史采购报价查询系统 V1.0 API 接口设计

> 本文档是 POM 的 API 接口详细设计文档。正文只描述接口本身需要冻结的内容：接口说明、方法、路径、请求参数、响应结果、业务错误码。本文档不定义前后端实现类、数据库表结构，也不绑定具体访问控制模型。

## 文档信息

| 项目 | 内容 |
| --- | --- |
| 项目名称 | POM 历史采购报价查询系统 |
| 版本/阶段 | V1.0 MVP / 接口详细设计 |
| 对应功能详细设计 | [docs/03-功能详细设计.md](../03-功能详细设计.md) |
| 对应 UI 主控文档 | [docs/04-前端UI设计/00-主控文档.md](./04-前端UI设计/00-主控文档.md) |
| 创建日期 | 2026-09-09 |
| 最后更新 | 2026-09-09 |
| 文档状态 | DRAFT |

## 1. 文档定位

### 1.1 文档职责边界

- 本文档负责：
  - 定义 POM 对外暴露的接口清单和逐接口详细设计
  - 固化每条接口最基本且必须明确的元素：接口说明、Method、Path、请求参数、响应结果、错误码
  - 为后续 OpenAPI（FastAPI 自动生成）、后端接口实现、前端调用封装、联调用例提供直接输入
- 本文档不负责：
  - 定义 Python 类、TypeScript 类型、页面状态、数据库表结构、索引和迁移脚本
  - 替代功能详细设计中的业务范围、规则和验收标准
  - 冻结具体访问控制码、角色矩阵或某一套系统专属安全设计（角色边界引用 docs/03 5.1 矩阵）

### 1.2 输入基线

| 文档类型 | 文档名称 | 用途 | 是否强约束 |
| --- | --- | --- | --- |
| 功能详细设计 | [docs/03-功能详细设计.md](../03-功能详细设计.md) | 业务范围、规则、状态、验收基线 | 是 |
| 架构/版本文档 | [docs/02-架构设计.md](../02-架构设计.md)、[docs/01-版本规划.md](../01-版本规划.md) | 服务边界、部署约束、版本范围 | 是 |
| API 和 DB 任务清单 | [docs/07-API和数据库任务清单.md](./07-API和数据库任务清单.md) | 模块推进顺序和完成状态 | 是 |
| 现有 OpenAPI / 错误码 | N/A（当前仓库不存在已冻结事实源） | 后续专项契约落地 | 否 |

### 1.3 契约分层约定

- 功能详细设计回答"为什么有这个接口、业务规则是什么"。
- 本文档回答"接口怎么设计、传什么、回什么、什么情况拒绝"。
- OpenAPI 回答"最终机器可读契约长什么样"（由 FastAPI 按本文档实现后自动生成 /docs）。
- 数据库设计回答"数据如何落表和约束"。

### 1.4 单接口固定结构

后续所有接口新增或改写时，统一按以下顺序组织：

1. 接口说明
2. Method / Path
3. Path 参数
4. Query 参数
5. Body 参数
6. 成功响应
7. 业务规则
8. 业务错误码

其中"业务规则"仅记录接口级承接约束，例如前置条件、状态影响、并发/幂等、只读限制、副作用和审计要求；功能详细设计中的模块级总规则、角色职责、状态机和验收口径不在单接口下重写。

## 2. 全局接口约定

### 2.1 Base Path 与版本

- Base Path：`/api/v1`
- 版本策略：破坏性变更升 `/api/v2`；V1.0 内仅做向后兼容新增

### 2.2 认证与安全边界

- 登录、token 签发、会话撤销由本系统 MOD-01 提供（JWT Bearer + 服务端会话撤销，见 docs/02 ADR-004）
- 除登录外所有接口需 `Authorization: Bearer <token>`；无效/撤销/过期会话返回 401
- 角色边界引用 docs/03 5.1 矩阵；未授权返回 403
- 认证后的响应设置 `Cache-Control: no-store`（PRD 8.2 禁缓存要求）

### 2.3 列表接口公共参数

列表接口默认继承以下公共查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `page` | number | 否 | 页码，默认 `1` |
| `pageSize` | number | 否 | 每页条数，默认 `20`，最大 `100` |
| `sortField` | string | 否 | 排序字段（各接口白名单校验） |
| `sortOrder` | string | 否 | 排序方向，`asc` / `desc` |

### 2.4 请求参数约定

- Path 参数只放资源主键或稳定业务标识。
- Query 参数只用于筛选、分页、排序和显式查询开关。
- Body 参数只放业务数据，不放认证、会话、数据库实现字段。
- 写接口默认使用 `version` 做乐观并发控制；若某接口不需要，会在接口章节单独注明。

### 2.5 响应结果约定

- 统一响应包裹：`{"code": 0, "message": "ok", "data": <业务体>}`；业务失败 code=错误码，HTTP 状态同步 4xx/5xx
- 列表接口业务体默认返回：`total` / `page` / `pageSize` / `items[]`
- 详情接口返回当前资源的完整业务视图
- 校验类接口返回稳定结论、失败码和失败原因摘要
- 敏感字段按角色返回：`user` 角色返回脱敏值并附 `masked_fields[]` 标记（docs/03 R-SYS-06/07）

### 2.6 状态、幂等与审计约定

- 主档状态基线见 docs/03 5.2 字典；本系统核心枚举：数据质量状态、批次状态、用户状态、行级导入状态
- 普通更新接口不承担状态切换语义；状态切换统一走专用动作接口（如 `PATCH /quotes/{id}/status`）
- 创建、状态切换、删除、导入提交、文件下载、敏感查看都必须有审计说明（事件字典 docs/03 R-SYS-01）
- 幂等、并发、重试要求在逐接口章节明确；导入提交使用 `commit_token` 幂等

### 2.7 越界内容禁止项

以下内容禁止写入 API 设计正文作为"接口定义"：

- Pydantic/TS 类型类名、前端请求封装类、页面状态类
- Repository / Table 设计、SQL 字段类型、索引、DDL 语句
- 具体访问控制码、角色矩阵、菜单路由树（引用 docs/03 与 UI 主控）

## 3. 接口目录

#### MOD-01 认证与用户

- 登录：`POST /api/v1/auth/login`
- 退出：`POST /api/v1/auth/logout`
- 当前用户信息：`GET /api/v1/auth/me`
- 用户列表：`GET /api/v1/users`
- 新建用户：`POST /api/v1/users`
- 编辑用户：`PATCH /api/v1/users/{id}`
- 重置密码：`POST /api/v1/users/{id}/reset-password`

#### MOD-02 核心业务对象与查询

- 报价搜索：`GET /api/v1/quotes/search`
- 报价详情：`GET /api/v1/quotes/{id}`
- 供应商选项列表：`GET /api/v1/suppliers/options`
- 使用单位选项列表：`GET /api/v1/meta/units`
- 原始文件下载：`GET /api/v1/files/{fileId}`

#### MOD-03 Excel 导入

- 上传文件：`POST /api/v1/imports/upload`
- 获取预览（识别/映射/行级校验）：`GET /api/v1/imports/{batchId}/preview`
- 修改预览参数（工作表/表头行/映射）：`PUT /api/v1/imports/{batchId}/preview`
- 确认入库：`POST /api/v1/imports/{batchId}/commit`
- 批次报告：`GET /api/v1/imports/{batchId}/report`
- 保存映射模板：`POST /api/v1/mapping-templates`
- 映射模板列表：`GET /api/v1/mapping-templates`
- 批次列表：`GET /api/v1/batches`
- 批次详情：`GET /api/v1/batches/{batchId}`

#### MOD-04 数据维护与修订

- 修正结构化字段：`PATCH /api/v1/quotes/{id}`
- 软删除报价：`DELETE /api/v1/quotes/{id}`
- 恢复报价：`POST /api/v1/quotes/{id}/restore`
- 标记数据质量状态：`PATCH /api/v1/quotes/{id}/status`
- 修订记录列表：`GET /api/v1/quotes/{id}/revisions`

#### MOD-05 系统管理与审计

- 审计日志查询：`GET /api/v1/audit`
- 备份状态：`GET /api/v1/admin/backup-status`

## 4. 模块详细设计

### 4.1 [MOD-01] 认证与用户

> 承接 F-001~F-004。会话语义：JWT(jti)+服务端会话撤销（docs/02 ADR-004）；角色边界见 docs/03 5.1。

#### 4.1.1 登录

- 接口说明：账号密码登录，成功后签发会话令牌
- Method / Path：`POST /api/v1/auth/login`

Path 参数：无

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `username` | string | 是 | 账号，4-32 位字母数字下划线 |
| `password` | string | 是 | 密码明文（HTTPS 传输） |

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `token` | string | JWT，有效期默认 12h |
| `expires_at` | string | 会话过期时间 ISO8601 |
| `user` | object | `{id, username, display_name, role}` |

业务规则（仅接口级承接）

- 触发限速（R-AUTH-11/12）时返回 429 并附剩余秒数；锁定期间正确密码同样拒绝
- 失败提示统一文案，不区分账号不存在/密码错误（R-AUTH-04）
- 副作用：写审计 LOGIN / LOGIN_FAILED；停用账号拒绝登录并写审计
- 本接口不需要 Bearer；响应 `Cache-Control: no-store`

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `10401` | 账号或密码错误 |
| `10402` | 失败次数过多，已临时锁定（附 `retry_after` 秒） |
| `10403` | 账号已停用 |

#### 4.1.2 退出

- 接口说明：撤销当前会话
- Method / Path：`POST /api/v1/auth/logout`

Path 参数：无

Query 参数：无

Body 参数：无

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `success` | boolean | 固定 true |

业务规则（仅接口级承接）

- 撤销服务端会话记录，此后旧令牌即失效（R-AUTH-03）；幂等：重复调用同样成功
- 副作用：写审计 LOGOUT

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `10403` | 会话已无效（幂等成功场景外：令牌签名非法仍返回 401 HTTP） |

#### 4.1.3 当前用户信息

- 接口说明：返回当前会话用户与权限摘要，用于前端菜单显隐
- Method / Path：`GET /api/v1/auth/me`

Path 参数：无

Query 参数：无

Body 参数：无

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | number | 用户 ID |
| `username` | string | 账号 |
| `display_name` | string | 姓名 |
| `role` | string | `user` / `maintainer` / `admin` |
| `session_expires_at` | string | 会话过期时间 |

业务规则（仅接口级承接）

- 只读；需有效会话；会话剩余 <30 分钟时前端据 `session_expires_at` 提示续期

业务错误码：无（401 由 HTTP 层统一返回）

#### 4.1.4 用户列表

- 接口说明：分页查询用户（admin 专用）
- Method / Path：`GET /api/v1/users`

Path 参数：无

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| 公共分页参数 | — | 否 | 见 2.3，`sortField` 白名单：`created_at`/`username` |
| `keyword` | string | 否 | 匹配账号/姓名 |
| `role` | string | 否 | 角色过滤 |
| `status` | string | 否 | `enabled`/`disabled` |

成功响应：`total/page/pageSize/items[]`，item 含 `{id, username, display_name, role, status, created_at, last_login_at}`

业务规则（仅接口级承接）

- 仅 admin（403 兜底）；只读

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `10404` | 无权限 |

#### 4.1.5 新建用户

- 接口说明：创建账号并返回一次性初始密码
- Method / Path：`POST /api/v1/users`

Path 参数：无

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `username` | string | 是 | 唯一，4-32 位 |
| `display_name` | string | 是 | 姓名 |
| `role` | string | 是 | `user`/`maintainer`/`admin` |

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | number | 新用户 ID |
| `initial_password` | string | 随机初始密码，仅本次返回（R-AUTH-07） |

业务规则（仅接口级承接）

- 仅 admin；不公开注册（R-AUTH-05）；密码服务端生成并哈希存储
- 副作用：写审计 USER_CREATE

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `10502` | 账号已存在 |
| `10404` | 无权限 |

#### 4.1.6 编辑用户

- 接口说明：修改姓名/角色/状态（启停）
- Method / Path：`PATCH /api/v1/users/{id}`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | number | 是 | 用户 ID |

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `display_name` | string | 否 | 姓名 |
| `role` | string | 否 | 角色 |
| `status` | string | 否 | `enabled`/`disabled`（停用即撤销全部会话，R-AUTH-06） |
| `version` | number | 是 | 乐观锁版本号 |

成功响应：返回更新后的 `{id, username, display_name, role, status, version}`

业务规则（仅接口级承接）

- 仅 admin；停用最后一个 admin 被拒绝；不允许停用自己
- 副作用：写审计 USER_DISABLE / 状态或角色变更记录

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `10501` | 用户不存在 |
| `10503` | 不允许的操作（如停用最后一个管理员/停用自己） |
| `10504` | 版本冲突，请刷新重试 |
| `10404` | 无权限 |

#### 4.1.7 重置密码

- 接口说明：生成新随机密码，一次性返回
- Method / Path：`POST /api/v1/users/{id}/reset-password`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | number | 是 | 用户 ID |

Query 参数：无

Body 参数：无

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `new_password` | string | 一次性明文密码 |

业务规则（仅接口级承接）

- 仅 admin；重置后该用户全部会话撤销
- 副作用：写审计 USER_RESET

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `10501` | 用户不存在 |
| `10404` | 无权限 |

### 4.2 [MOD-02] 核心业务对象与查询

> 承接 F-012~F-019。数据由 MOD-03 导入写入；本模块负责读取与追溯。

#### 4.2.1 报价搜索

- 接口说明：关键词+组合筛选查询结构化报价列表
- Method / Path：`GET /api/v1/quotes/search`

Path 参数：无

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | string | 否 | 多词空格分隔 AND；搜索域见 R-QRY-01 |
| `date_from` / `date_to` | string(date) | 否 | 报价日期区间 |
| `supplier_id` | number | 否 | 供应商 |
| `unit` | string | 否 | 使用单位 |
| `status` | string | 否 | 数据质量状态（2.4 字典，`deleted` 仅 admin 显式查询） |
| `price_min` / `price_max` | number | 否 | 金额区间（元） |
| `tax_included` / `freight_included` | boolean | 否 | 含税/含运 |
| `sortField` | string | 否 | 白名单：`quote_date`（默认，降序）/`amount`/`created_at` |
| `sortOrder` | string | 否 | `asc`/`desc`，默认 `desc`；日期空值排最后 |
| `page` / `pageSize` | number | 否 | 见 2.3 |

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `total` / `page` / `pageSize` | number | 分页 |
| `items[]` | array | 行结构见下 |
| `items[].id` | number | 报价 ID |
| `items[].material_name` / `material_code` / `spec_model` / `brand` | string | 物料摘要 |
| `items[].supplier_name` | string | 供应商（可"待确认"） |
| `items[].amount` / `currency` | number/string | 金额（空为 null） |
| `items[].tax_included` / `freight_included` | boolean | — |
| `items[].quote_date` | string | 报价日期 |
| `items[].status` | string | 数据质量状态 |
| `items[].source_summary` | string | `文件名/工作表/R行号` 摘要 |
| `items[].batch_id` | number | 批次 |
| `masked_fields[]` | array | 本响应被脱敏的字段名（user 角色） |

业务规则（仅接口级承接）

- 只读；deleted 记录默认不出现在结果（R-QRY-03）
- 空结果返回 `items=[]` 与 `applied_filters`（请求参数回显），不伪造近似结果（R-QRY-10）
- URL 参数可完整重建查询（UI 分享/刷新保留）

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `20401` | 非法筛选参数（如 price_min > price_max） |

#### 4.2.2 报价详情

- 接口说明：单条报价全量聚合（物料/需求/报价/供应商/原始来源/兄弟报价）
- Method / Path：`GET /api/v1/quotes/{id}`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | number | 是 | 报价 ID |

Query 参数：无

Body 参数：无

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` / `version` | number | 报价 ID 与乐观锁版本 |
| `material{}` | object | 物料组全字段（docs/03 7.2） |
| `requirement{}` | object/null | 需求组（数量/单位/需求日期/接收人/报价行编号/备注） |
| `quote{}` | object | 金额/币种/含税/税率/含运/可供数量/交货日期/运输方式/报价日期/`date_inferred_from`/有效期/状态/报价备注 |
| `supplier{}` | object | 名称/联系人/电话/渠道（敏感字段按角色脱敏） |
| `source{}` | object | 文件名/工作表/行号/文件哈希前8位/批次号/上传人/上传时间 |
| `source.raw_cells{}` | object | 原始行快照：列名→值（只读，R-IMP-26） |
| `sibling_quotes[]` | array | 同一快照拆分的其他报价 `{id, supplier_name, amount, status}` |
| `masked_fields[]` | array | 被脱敏字段名 |

业务规则（仅接口级承接）

- 只读；记录 `deleted` 且非 admin 返回 404（不泄露存在性）
- user 角色敏感字段脱敏并写 SENSITIVE_VIEW 仅当返回明文（maintainer/admin）
- 需求日期等推断字段附 `date_inferred_from`（API-TBD-001 默认）

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `20402` | 记录不存在或已删除 |

#### 4.2.3 供应商选项列表

- 接口说明：筛选区供应商下拉（远程搜索）
- Method / Path：`GET /api/v1/suppliers/options`

Path 参数：无

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | string | 否 | 名称模糊匹配 |
| `limit` | number | 否 | 默认 20，最大 50 |

成功响应：`items[]: {id, name, status}`

业务规则（仅接口级承接）：只读；全角色；仅返回未删除供应商

业务错误码：无

#### 4.2.4 使用单位选项列表

- 接口说明：筛选区使用单位去重值
- Method / Path：`GET /api/v1/meta/units`

Path 参数：无

Query 参数：无

成功响应：`items[]: string`（单位名去重升序）

业务规则（仅接口级承接）：只读；全角色

业务错误码：无

#### 4.2.5 原始文件下载

- 接口说明：下载导入时的原始 Excel 文件（追溯核对）
- Method / Path：`GET /api/v1/files/{fileId}`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `fileId` | number | 是 | 源文件 ID |

Query 参数：无

Body 参数：无

成功响应：文件二进制流（Content-Disposition 附原始文件名）

业务规则（仅接口级承接）

- 全角色可下载获授权文件（5.1.1 矩阵）；响应流式输出，`Cache-Control: no-store`
- 副作用：写审计 FILE_DOWNLOAD；文件名由服务端规范化，杜绝路径穿越

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `20403` | 文件不存在或已丢失 |

### 4.3 [MOD-03] Excel 导入

> 承接 F-005~F-011。流程：upload → preview（可反复调参重解析）→ commit（单事务）→ report。

#### 4.3.1 上传文件

- 接口说明：multipart 批量上传 xls/xlsx，校验并创建批次
- Method / Path：`POST /api/v1/imports/upload`

Path 参数：无

Query 参数：无

Body 参数（multipart/form-data）

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `files` | file[] | 是 | 1..N 个 .xls/.xlsx，单文件 ≤20MB |

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `batch_id` | number | 新批次 ID |
| `files[]` | array | `{file_id, filename, size, sha256(前8位展示), check_status, check_message}` |
| `check_status` | string | `passed`/`failed`/`duplicate` |
| `duplicate_of_batch_id` | number | 重复文件指向的既有批次 |

业务规则（仅接口级承接）

- 校验扩展名+文件签名+大小+哈希（R-IMP-01/02）；单文件失败不影响其他文件（R-IMP-03）
- 文件哈希命中 → 该文件标记 duplicate 并阻止进入预览（R-IMP-18）
- 副作用：保存文件到隔离目录；写审计 IMPORT_UPLOAD

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `30401` | 无有效文件（全部失败/未选择） |
| `30402` | 文件超大小限制 |

#### 4.3.2 获取预览

- 接口说明：对批次内指定文件做表头识别、映射建议与行级校验预览
- Method / Path：`GET /api/v1/imports/{batchId}/preview`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `batchId` | number | 是 | 批次 ID |

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file_id` | number | 是 | 批次内文件 |
| `sheet_name` | string | 否 | 缺省取识别分最高的工作表 |
| `header_row` | number | 否 | 缺省取自动识别行 |

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `sheets[]` | array | `{name, row_count, detect_score, template_type}` |
| `header_row` | number | 自动识别的表头行 |
| `shift_detected` | boolean | 数据列整体位移检测结果（R-IMP-06） |
| `shift_message` | string | 位移说明 |
| `mappings[]` | array | `{standard_field, source_column, sample_value, matched_by_alias}` |
| `rows[]` | array | 行级预览：`{row_no, status(ok/warn/error/duplicate), quote_count, preview{amount,supplier,quote_date}, reasons[]}` |
| `summary` | object | `{ok, warn, error, duplicate}` 统计 |
| `mapping_templates[]` | array | 可复用模板候选（按表头指纹匹配） |

业务规则（仅接口级承接）

- 只读解析，不写业务表；识别规则引用 R-IMP-04~17
- 1000 行标准模板 ≤60s（性能目标，docs/02 10.2）

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `30403` | 文件无法解析（加密/损坏） |
| `30404` | 表头无法识别（可进入人工映射，非致命） |

#### 4.3.3 修改预览参数

- 接口说明：用户确认/修改工作表、表头行、列映射后重新解析
- Method / Path：`PUT /api/v1/imports/{batchId}/preview`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `batchId` | number | 是 | 批次 ID |

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `file_id` | number | 是 | 文件 |
| `sheet_name` | string | 是 | 工作表 |
| `header_row` | number | 是 | 表头行号 |
| `mappings[]` | array | 是 | `{standard_field, source_column}` 全量映射 |
| `skip_error_rows` | boolean | 否 | 默认 false |

成功响应：与 4.3.2 行级预览结构一致（`rows[]`/`summary`/`shift_detected`）

业务规则（仅接口级承接）

- 同一源列不可重复映射；品牌列不得映射到供应商（R-IMP-08）
- 幂等：相同参数重复提交结果一致

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `30405` | 映射冲突（源列重复/必填映射缺失） |

#### 4.3.4 确认入库

- 接口说明：按预览结果以单事务写入结构化数据
- Method / Path：`POST /api/v1/imports/{batchId}/commit`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `batchId` | number | 是 | 批次 ID |

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `commit_token` | string | 是 | 预览响应返回的幂等令牌 |
| `file_commits[]` | array | 是 | 每文件 `{file_id, sheet_name, header_row, mappings[], skip_error_rows}` |

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `report` | object | `{success, skipped, failed, needs_review, batch_status}` |

业务规则（仅接口级承接）

- 幂等：同 `commit_token` 重复提交返回首次结果，不重复入库
- 单事务：任一文件写入失败整批回滚，批次状态=failed（R-IMP-23）
- 副作用：写物料/需求/供应商/报价/快照/行级结果；写审计 IMPORT_COMMIT

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `30406` | 存在错误行且未允许跳过 |
| `30407` | commit_token 与预览不一致（需重新预览） |
| `30408` | 批次已提交（幂等命中或状态冲突） |

#### 4.3.5 批次报告

- 接口说明：批次处理结果与行级原因
- Method / Path：`GET /api/v1/imports/{batchId}/report`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `batchId` | number | 是 | 批次 ID |

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | string | 否 | 行级状态过滤 |
| 公共分页参数 | — | 否 | 见 2.3 |

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `batch` | object | `{id, status, uploaded_by, uploaded_at}` |
| `summary` | object | `{success, skipped, failed, needs_review}` |
| `items[]` | array | `{file_name, sheet_name, row_no, status, quote_ids[], reasons[]}` |

业务规则（仅接口级承接）：只读；maintainer+；数量与行级明细一致（A-IMP-10）

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `30409` | 批次不存在 |

#### 4.3.6 保存映射模板

- 接口说明：将当前映射保存为可复用模板
- Method / Path：`POST /api/v1/mapping-templates`

Path 参数：无

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 模板名（同账号内唯一） |
| `header_fingerprint` | string | 是 | 表头指纹（预览响应返回） |
| `mappings[]` | array | 是 | `{standard_field, source_column}` |
| `sheet_hint` | string | 否 | 建议工作表名 |

成功响应：`{id, name}`

业务规则（仅接口级承接）：maintainer+；副作用写审计（IMPORT 模板变更并入审计）；幂等按 name+归属人唯一

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `30410` | 模板名已存在 |

#### 4.3.7 映射模板列表

- 接口说明：当前账号可用模板
- Method / Path：`GET /api/v1/mapping-templates`

Path 参数：无

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `header_fingerprint` | string | 否 | 按指纹匹配推荐模板 |

成功响应：`items[]: {id, name, sheet_hint, mappings[], created_at}`

业务规则（仅接口级承接）：只读；maintainer+；模板按创建人隔离

业务错误码：无

#### 4.3.8 批次列表

- 接口说明：分页查询导入批次（maintainer+）
- Method / Path：`GET /api/v1/batches`

Path 参数：无

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `keyword` | string | 否 | 批次号/文件名 |
| `status` | string | 否 | 批次状态 |
| `uploaded_from` / `uploaded_to` | string(date) | 否 | 上传时间区间 |
| 公共分页参数 | — | 否 | `sortField` 白名单：`created_at` |

成功响应：`total/page/pageSize/items[]`，item：`{id, file_count, uploaded_by_name, created_at, success_count, skipped_count, failed_count, status}`

业务规则（仅接口级承接）：maintainer 查本人批次；admin 查全部（docs/03 5.1.1）

业务错误码：无

#### 4.3.9 批次详情

- 接口说明：批次概要+源文件+行级明细
- Method / Path：`GET /api/v1/batches/{batchId}`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `batchId` | number | 是 | 批次 ID |

Query 参数：无

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `batch` | object | 同 4.3.8 item + summary |
| `files[]` | array | `{file_id, filename, sha256, size, check_status}` |
| `row_results[]` | array | 同 4.3.5 items + 每行关联 quote 当前 status（含 deleted 标记） |

业务规则（仅接口级承接）：只读；deleted 报价对非 admin 显示"已删除"标记但不返回内容

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `30409` | 批次不存在 |

### 4.4 [MOD-04] 数据维护与修订

> 承接 F-020~F-022。所有写操作留痕（前后值+原因）；快照不可变（R-IMP-26）。

#### 4.4.1 修正结构化字段

- 接口说明：维护员修正报价的结构化字段
- Method / Path：`PATCH /api/v1/quotes/{id}`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | number | 是 | 报价 ID |

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `fields` | object | 是 | 待改字段键值（可改集合见 R-MNT-01；来源组字段拒绝） |
| `reason` | string | 是 | 修改原因（必填） |
| `version` | number | 是 | 乐观锁版本 |

成功响应：`{id, version(新), changed_fields[]}`

业务规则（仅接口级承接）

- maintainer+；user 403（R-AUTH-09）
- 并发：version 不一致返回冲突，不覆盖（UI 分册 D 并发提示）
- 副作用：写 quote_revision（旧值/新值/原因/人/时间）；写审计 QUOTE_UPDATE；快照不变

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `40401` | 记录不存在或已删除 |
| `40402` | 字段不可修改（来源组） |
| `40403` | 原因必填 |
| `40404` | 版本冲突 |
| `10404` | 无权限 |

#### 4.4.2 软删除报价

- 接口说明：删除后默认不在查询出现（FR19）
- Method / Path：`DELETE /api/v1/quotes/{id}`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | number | 是 | 报价 ID |

Query 参数：无

Body 参数：无

成功响应：`{id, status: "deleted"}`

业务规则（仅接口级承接）

- maintainer+；兄弟报价不受影响；幂等：已删除再删同样成功
- 副作用：status→deleted；写审计 QUOTE_DELETE

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `40401` | 记录不存在 |
| `10404` | 无权限 |

#### 4.4.3 恢复报价

- 接口说明：管理员恢复软删除记录（FR19）
- Method / Path：`POST /api/v1/quotes/{id}/restore`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | number | 是 | 报价 ID |

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `reason` | string | 是 | 恢复原因 |

成功响应：`{id, status: "auto_extracted|confirmed(原值)"}`

业务规则（仅接口级承接）

- 仅 admin（R-MNT-04）；仅 deleted 状态可恢复
- 副作用：写审计 QUOTE_RESTORE

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `40401` | 记录不存在 |
| `40405` | 记录未处于删除状态 |
| `10404` | 无权限 |

#### 4.4.4 标记数据质量状态

- 接口说明：人工标记待核对/无有效价格/字段缺失/已确认（FR20）
- Method / Path：`PATCH /api/v1/quotes/{id}/status`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | number | 是 | 报价 ID |

Query 参数：无

Body 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `status` | string | 是 | 目标状态（不含 deleted，删除走 4.4.2） |
| `reason` | string | 是 | 标记原因 |

成功响应：`{id, status}`

业务规则（仅接口级承接）

- maintainer+；状态值域校验（docs/03 5.2）
- 副作用：写修订记录（status 字段变更）+ 审计 STATUS_MARK

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `40401` | 记录不存在 |
| `40406` | 非法状态值 |
| `10404` | 无权限 |

#### 4.4.5 修订记录列表

- 接口说明：查询该报价的全部修改历史
- Method / Path：`GET /api/v1/quotes/{id}/revisions`

Path 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | number | 是 | 报价 ID |

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| 公共分页参数 | — | 否 | 默认按时间倒序 |

成功响应：`total/page/pageSize/items[]`，item：`{id, field, old_value, new_value, reason, changed_by_name, changed_at}`

业务规则（仅接口级承接）

- maintainer+ 可见（user 不可见该 Tab，UI 分册 B）；只读 append-only

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `40401` | 记录不存在 |

### 4.5 [MOD-05] 系统管理与审计

> 承接 F-023~F-025。审计事件字典见 docs/03 R-SYS-01。

#### 4.5.1 审计日志查询

- 接口说明：分页查询审计记录（admin 专用）
- Method / Path：`GET /api/v1/audit`

Path 参数：无

Query 参数

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `time_from` / `time_to` | string(datetime) | 否 | 时间区间 |
| `actor_id` | number | 否 | 操作人 |
| `action` | string | 否 | 动作（R-SYS-01 字典） |
| `object_type` | string | 否 | 对象类型（quote/user/import_batch/file） |
| `keyword` | string | 否 | 摘要模糊匹配 |
| 公共分页参数 | — | 否 | `sortField` 白名单：`created_at` |

成功响应：`total/page/pageSize/items[]`，item：`{id, created_at, actor_id, actor_name, action, object_type, object_id, result, summary, detail}`

业务规则（仅接口级承接）

- 仅 admin；只读；`detail` 含变化前后值 JSON（USER_CREATE 的 initial_password 不入审计）
- 默认时间倒序；审计不可修改删除

业务错误码

| 错误码 | 说明 |
| --- | --- |
| `50401` | 非法动作过滤值 |
| `10404` | 无权限 |

#### 4.5.2 备份状态

- 接口说明：返回最近备份产物列表与告警状态（admin 专用）
- Method / Path：`GET /api/v1/admin/backup-status`

Path 参数：无

Query 参数：无

成功响应

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `alert` | object/null | `{level, message}`；连续 2 天无成功备份时非空 |
| `items[]` | array | `{backup_date, type(db+files), size_bytes, status, artifact_name}` |
| `retention_days` | number | 当前保留周期配置 |

业务规则（仅接口级承接）

- 仅 admin；只读；数据来自备份目录扫描（无备份表）；备份执行由部署侧 cron 完成（docs/02 3.4）

业务错误码：无

## 5. 契约同步清单

### 5.1 OpenAPI 同步

| 模块 ID | 目标契约文件 | 当前状态 |
| --- | --- | --- |
| 全部 | `backend/app/main.py` FastAPI 自动生成（/docs） | 按实现推进 |

### 5.2 错误码 / 监控同步

| 模块 ID | 当前状态 | 说明 |
| --- | --- | --- |
| 全部 | TODO | 业务错误码随模块细化时补齐并汇总至 2.5 错误模型 |

## 6. AI 实施摘要

| 模块 ID | 当前阶段 | 适合 AI 直接承接的内容 |
| --- | --- | --- |
| MOD-01 | DONE | 任务 API-DB-001：登录/会话/用户管理接口卡片 |
| MOD-02 | DONE | 任务 API-DB-002：搜索/详情/选项/下载接口卡片 |
| MOD-03 | DONE | 任务 API-DB-003：导入全流程接口卡片 |
| MOD-04 | DONE | 任务 API-DB-004：纠错/删除/恢复/标记/修订接口卡片 |
| MOD-05 | DONE | 任务 API-DB-005：审计/备份状态接口卡片 |

## 7. 待确认事项

| 编号 | 问题 | 影响模块 | 状态 |
| --- | --- | --- | --- |
| API-TBD-001 | 报价日期推断来源展示口径（推断时是否附推断依据字段） | MOD-02 | OPEN（默认：附 date_inferred_from） |
| API-TBD-002 | 文件下载是否需要防盗链短时签名 URL | MOD-02 | OPEN（默认：会话鉴权直下） |
