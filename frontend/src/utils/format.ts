/** 全局格式化工具（docs/04 主控 2.4） */

export function fmtAmount(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—'
  return String(v).replace('T', ' ').slice(0, 16)
}

export function fmtDate(v: string | null | undefined): string {
  if (!v) return '—'
  return String(v).slice(0, 10)
}

/** 手机号脱敏：139****4455（user 角色后端已脱敏，此工具供前端二次兜底） */
export function maskPhone(v: string | null | undefined): string {
  if (!v) return '—'
  const digits = v.replace(/\D/g, '')
  if (digits.length === 11) return v.replace(digits.slice(3, 7), '****')
  if (v.length >= 4) return v.slice(0, 2) + '****' + v.slice(-2)
  return '****'
}

export const APP_VERSION = '0.1.0.20260923'

/** 报价人显示：单字姓补齐 XX（用户约定），完整人名原样 */
export function fmtQuoter(v: string | null | undefined): string {
  if (!v) return '—'
  return v.length === 1 ? `${v}XX` : v
}

export const QUOTE_STATUS_MAP: Record<string, { label: string; tag: string }> = {
  confirmed: { label: '已确认', tag: 'success' },
  auto_extracted: { label: '自动识别', tag: 'info' },
  needs_review: { label: '待核对', tag: 'warning' },
  no_valid_price: { label: '无有效报价', tag: 'info' },
  deleted: { label: '已删除', tag: 'danger' },
}

export const BATCH_STATUS_MAP: Record<string, { label: string; tag: string }> = {
  pending: { label: '待提交', tag: 'info' },
  confirmed: { label: '已确认', tag: 'success' },
  failed: { label: '失败', tag: 'danger' },
  partial: { label: '部分成功', tag: 'warning' },
}

export const ROW_STATUS_MAP: Record<string, { label: string; tag: string }> = {
  ok: { label: '正常', tag: 'success' },
  warn: { label: '警告', tag: 'warning' },
  error: { label: '错误', tag: 'danger' },
  duplicate: { label: '重复', tag: 'info' },
  skipped_row: { label: '跳过', tag: 'info' },
}
