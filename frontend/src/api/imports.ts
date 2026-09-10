import http from './http'

export async function uploadFiles(files: File[]) {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  return await http.post<never, any>('/imports/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function getPreview(batchId: number | string, fileId: number, sheetName?: string, headerRow?: number) {
  return await http.get<never, any>(`/imports/${batchId}/preview`, {
    params: { file_id: fileId, sheet_name: sheetName, header_row: headerRow },
  })
}

export async function updatePreview(batchId: number | string, body: Record<string, unknown>) {
  return await http.put<never, any>(`/imports/${batchId}/preview`, body)
}

export async function commitImport(batchId: number | string, body: Record<string, unknown>) {
  return await http.post<never, any>(`/imports/${batchId}/commit`, body)
}

export async function getReport(batchId: number | string, params?: Record<string, unknown>) {
  return await http.get<never, any>(`/imports/${batchId}/report`, { params })
}

export async function saveTemplate(body: Record<string, unknown>) {
  return await http.post<never, any>('/mapping-templates', body)
}

export async function listTemplates(headerFingerprint?: string) {
  return await http.get<never, any>('/mapping-templates', { params: { header_fingerprint: headerFingerprint } })
}

export async function listBatches(params: Record<string, unknown>) {
  return await http.get<never, any>('/batches', { params })
}

export async function getBatch(batchId: number | string) {
  return await http.get<never, any>(`/batches/${batchId}`)
}
