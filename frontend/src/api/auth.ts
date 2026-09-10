import http from './http'

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: 'user' | 'maintainer' | 'admin'
  session_expires_at?: string
}

export async function login(username: string, password: string) {
  return await http.post<never, any>('/auth/login', { username, password })
}

export async function logout() {
  return await http.post<never, any>('/auth/logout')
}

export async function me(): Promise<UserInfo> {
  return await http.get<never, UserInfo>('/auth/me')
}
