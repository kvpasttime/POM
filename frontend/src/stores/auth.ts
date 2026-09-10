import { defineStore } from 'pinia'
import { ref } from 'vue'
import { me as apiMe, login as apiLogin, logout as apiLogout, UserInfo } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('pom_token') || '')
  const user = ref<UserInfo | null>(null)

  function setToken(t: string) {
    token.value = t
    localStorage.setItem('pom_token', t)
  }

  async function login(username: string, password: string, remember: boolean) {
    const data = await apiLogin(username, password)
    setToken(data.token)
    user.value = data.user
    if (remember) localStorage.setItem('pom_remember_username', username)
    else localStorage.removeItem('pom_remember_username')
    return data
  }

  async function fetchMe() {
    if (!token.value) return null
    try {
      user.value = await apiMe()
      return user.value
    } catch {
      user.value = null
      return null
    }
  }

  async function logout() {
    try {
      await apiLogout()
    } catch { /* 忽略 */ }
    token.value = ''
    user.value = null
    localStorage.removeItem('pom_token')
  }

  return { token, user, login, fetchMe, logout, setToken }
})
