import http from './http'

export async function queryAudit(params: Record<string, unknown>) {
  return await http.get<never, any>('/audit', { params })
}

export async function backupStatus() {
  return await http.get<never, any>('/admin/backup-status')
}
