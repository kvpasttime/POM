import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', redirect: '/search' },
      { path: 'search', name: 'search', component: () => import('../views/search/QuoteSearch.vue') },
      { path: 'quotes/:id', name: 'quote-detail', component: () => import('../views/search/QuoteDetail.vue') },
      { path: 'quotes/:id/edit', name: 'quote-edit', component: () => import('../views/search/QuoteEdit.vue'), meta: { roles: ['maintainer', 'admin'] } },
      { path: 'requirements/:id', name: 'requirement-detail', component: () => import('../views/search/RequirementDetail.vue') },
      { path: 'import', name: 'import', component: () => import('../views/import/UploadPage.vue'), meta: { roles: ['maintainer', 'admin'] } },
      { path: 'import/:batchId/map', name: 'import-map', component: () => import('../views/import/MapPreviewPage.vue'), meta: { roles: ['maintainer', 'admin'] } },
      { path: 'import/:batchId/report', name: 'import-report', component: () => import('../views/import/ReportPage.vue'), meta: { roles: ['maintainer', 'admin'] } },
      { path: 'batches', name: 'batches', component: () => import('../views/import/BatchesPage.vue'), meta: { roles: ['maintainer', 'admin'] } },
      { path: 'batches/:id', name: 'batch-detail', component: () => import('../views/import/BatchDetailPage.vue'), meta: { roles: ['maintainer', 'admin'] } },
      { path: 'users', name: 'users', component: () => import('../views/admin/UsersPage.vue'), meta: { roles: ['admin'] } },
      { path: 'audit', name: 'audit', component: () => import('../views/admin/AuditPage.vue'), meta: { roles: ['admin'] } },
      { path: 'backup', name: 'backup', component: () => import('../views/admin/BackupPage.vue'), meta: { roles: ['admin'] } },
    ],
  },
  { path: '/:pathMatch(.*)*', component: () => import('../views/NotFound.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) return true
  if (!auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  // R-UI-02/R-AUTH-06：会话与用户状态以服务端为准
  if (!auth.user) {
    const u = await auth.fetchMe()
    if (!u) return { path: '/login', query: { redirect: to.fullPath } }
  }
  const roles = to.meta.roles as string[] | undefined
  if (roles && auth.user && !roles.includes(auth.user.role)) {
    return { path: '/403' }
  }
  return true
})

export default router
