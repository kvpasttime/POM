import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const http = axios.create({ baseURL: '/api/v1', timeout: 120000 })

http.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('pom_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      // 业务错误码：会话失效 → 跳登录（R-UI-02）
      if (body.code === 10403 || resp.status === 401) {
        localStorage.removeItem('pom_token')
        if (router.currentRoute.value.path !== '/login') {
          ElMessage.error(body.message || '登录已过期')
          router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
        }
        return Promise.reject(body)
      }
      ElMessage.error(body.message || '操作失败')
      return Promise.reject(body)
    }
    return body
  },
  (err) => {
    const status = err.response?.status
    const body = err.response?.data
    const message = body?.message || err.message || '网络错误'
    if (status === 401) {
      localStorage.removeItem('pom_token')
      if (router.currentRoute.value.path !== '/login') {
        ElMessage.error(message)
        router.push({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    } else {
      ElMessage.error(message)
    }
    return Promise.reject(body || err)
  },
)

export default http
