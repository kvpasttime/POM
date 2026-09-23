<template>
  <el-container style="height: 100vh">
    <!-- 侧边栏 -->
    <el-aside width="228px" class="sidebar">
      <div class="brand">
        <div class="brand-logo">P</div>
        <div class="brand-text">
          <div class="brand-name">POM</div>
          <div class="brand-sub">采购报价库</div>
        </div>
      </div>
      <el-scrollbar class="menu-scroll">
        <el-menu :default-active="activeMenu" router class="side-menu"
                 background-color="transparent" text-color="#94a3b8" active-text-color="#ffffff">
          <el-menu-item index="/search">
            <el-icon><Search /></el-icon><span>报价搜索</span>
          </el-menu-item>
          <el-menu-item v-if="isMaintainer" index="/import">
            <el-icon><Upload /></el-icon><span>数据导入</span>
          </el-menu-item>
          <el-menu-item v-if="isMaintainer" index="/batches">
            <el-icon><Folder /></el-icon><span>导入批次</span>
          </el-menu-item>
          <template v-if="isAdmin">
            <el-menu-item index="/users">
              <el-icon><User /></el-icon><span>用户管理</span>
            </el-menu-item>
            <el-menu-item index="/audit">
              <el-icon><Document /></el-icon><span>审计日志</span>
            </el-menu-item>
            <el-menu-item index="/backup">
              <el-icon><Box /></el-icon><span>备份状态</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>
      <div class="sidebar-foot">v{{ APP_VERSION }}</div>
    </el-aside>

    <el-container class="right">
      <!-- 顶栏 -->
      <el-header class="topbar" height="60px">
        <div class="page-title">{{ pageTitle }}</div>
        <div class="spacer" />
        <el-dropdown v-if="auth.user" trigger="click" @command="onCommand">
          <div class="user-chip">
            <div class="avatar">{{ auth.user.display_name?.slice(0, 1) || 'U' }}</div>
            <div class="user-meta">
              <div class="user-name">{{ auth.user.display_name }}</div>
              <div class="user-role">{{ roleLabel }}</div>
            </div>
            <el-icon color="#94a3b8"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                <el-icon><User /></el-icon>{{ auth.user.username }}
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, Upload, Folder, User, Document, Box, ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { APP_VERSION } from '../utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const roleLabel = computed(() => {
  const map: Record<string, string> = { user: '普通用户', maintainer: '数据维护员', admin: '系统管理员' }
  return auth.user ? map[auth.user.role] || auth.user.role : ''
})
const isMaintainer = computed(() => auth.user && ['maintainer', 'admin'].includes(auth.user.role))
const isAdmin = computed(() => auth.user?.role === 'admin')
const activeMenu = computed(() => '/' + (route.path.split('/')[1] || 'search'))

const TITLES: Record<string, string> = {
  '/search': '报价搜索',
  '/import': '数据导入',
  '/batches': '导入批次',
  '/users': '用户管理',
  '/audit': '审计日志',
  '/backup': '备份状态',
}
const pageTitle = computed(() => TITLES[activeMenu.value] || '报价详情')

async function onCommand(cmd: string) {
  if (cmd === 'logout') {
    await auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.sidebar {
  background: linear-gradient(180deg, #0f172a 0%, #131c33 100%);
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(148, 163, 184, 0.12);
}
.brand {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 20px 16px;
}
.brand-logo {
  width: 36px; height: 36px; border-radius: 10px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff; font-weight: 800; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}
.brand-name { color: #f1f5f9; font-weight: 700; font-size: 15px; line-height: 1.2; }
.brand-sub { color: #64748b; font-size: 11px; }

.menu-scroll { flex: 1; }
.side-menu { border-right: none; padding: 6px 10px; }
.side-menu :deep(.el-menu-item) {
  border-radius: 8px; margin: 3px 0; height: 44px;
  transition: all 0.15s ease;
}
.side-menu :deep(.el-menu-item:hover) {
  background: rgba(148, 163, 184, 0.1);
}
.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.35);
}
.side-menu :deep(.el-menu-item .el-icon) { margin-right: 8px; font-size: 16px; }
.sidebar-foot {
  padding: 12px 20px; color: #475569; font-size: 11px;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
}

.right { min-width: 0; }
.topbar {
  display: flex; align-items: center;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #edf0f5;
}
.page-title { font-size: 15px; font-weight: 600; color: #0f172a; }
.spacer { flex: 1; }
.user-chip {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 10px; border-radius: 10px; cursor: pointer;
  transition: background 0.15s ease;
}
.user-chip:hover { background: #f1f5f9; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; font-size: 14px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}
.user-meta { text-align: left; line-height: 1.2; }
.user-name { font-size: 13px; font-weight: 600; color: #0f172a; }
.user-role { font-size: 11px; color: #94a3b8; }

.main {
  background: var(--pom-bg);
  padding: 18px 22px;
  overflow: auto;
}
</style>
