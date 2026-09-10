import http from './http'

export interface UserItem {
  id: number
  username: string
  display_name: string
  role: string
  status: string
  created_at: string | null
  last_login_at: string | null
  version: number
}

export async function listUsers(params: Record<string, unknown>) {
  return await http.get<never, any>('/users', { params })
}

export async function createUser(body: { username: string; display_name: string; role: string }) {
  return await http.post<never, any>('/users', body)
}

export async function updateUser(id: number, body: Record<string, unknown>) {
  return await http.patch<never, any>(`/users/${id}`, body)
}

export async function resetPassword(id: number) {
  return await http.post<never, any>(`/users/${id}/reset-password`)
}
