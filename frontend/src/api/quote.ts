import http from './http'

export interface SearchParams {
  keyword?: string
  date_from?: string
  date_to?: string
  supplier_id?: number
  unit?: string
  status?: string
  price_min?: number
  price_max?: number
  tax_included?: boolean | null
  freight_included?: boolean | null
  sortField?: string
  sortOrder?: string
  page?: number
  pageSize?: number
  include_requirement?: boolean
}

export async function searchQuotes(params: SearchParams) {
  // 清理空值参数
  const clean: Record<string, unknown> = {}
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') clean[k] = v
  })
  return await http.get<never, any>('/quotes/search', { params: clean })
}

export async function requirementDetail(id: number | string) {
  return await http.get<never, any>(`/requirements/${id}`)
}

export async function quoteDetail(id: number | string) {
  return await http.get<never, any>(`/quotes/${id}`)
}

export async function quoteRevisions(id: number | string, params?: Record<string, unknown>) {
  return await http.get<never, any>(`/quotes/${id}/revisions`, { params })
}

export async function patchQuote(id: number | string, body: Record<string, unknown>) {
  return await http.patch<never, any>(`/quotes/${id}`, body)
}

export async function deleteQuote(id: number | string) {
  return await http.delete<never, any>(`/quotes/${id}`)
}

export async function restoreQuote(id: number | string, reason: string) {
  return await http.post<never, any>(`/quotes/${id}/restore`, { reason })
}

export async function markStatus(id: number | string, status: string, reason: string) {
  return await http.patch<never, any>(`/quotes/${id}/status`, { status, reason })
}

export async function supplierOptions(keyword?: string, limit = 20) {
  return await http.get<never, any>('/suppliers/options', { params: { keyword, limit } })
}

export async function unitOptions() {
  return await http.get<never, any>('/meta/units')
}

export function fileDownloadUrl(fileId: number) {
  return `/api/v1/files/${fileId}`
}
