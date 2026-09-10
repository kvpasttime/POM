<template>
  <el-container style="height: 100vh">
    <el-header class="topbar">
      <div class="brand" @click="$router.push('/search')">POM 采购报价库</div>
      <div class="spacer" />
      <el-dropdown v-if="auth.user" @command="onCommand">
        <span class="user-name">{{ auth.user.display_name }}（{{ roleLabel }}）<el-icon><ArrowDown /></el-icon></span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-header>
    <el-container>
      <el-aside width="200px" class="sidebar">
        <el-menu :default-active="activeMenu" router>
          <el-menu-item index="/search">报价搜索</el-menu-item>
          <el-menu-item v-if="isMaintainer" index="/import">数据导入</el-menu-item>
          <el-menu-item v-if="isMaintainer" index="/batches">导入批次</el-menu-item>
          <template v-if="isAdmin">
            <el-menu-item index="/users">用户管理</el-menu-item>
            <el-menu-item index="/audit">审计日志</el-menu-item>
            <el-menu-item index="/backup">备份状态</el-menu-item>
          </template>
        </el-menu>
      </el-aside>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

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

async function onCommand(cmd: string) {
  if (cmd === 'logout') {
    await auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.topbar { display: flex; align-items: center; background: #409eff; color: #fff; }
.brand { font-size: 18px; font-weight: 600; cursor: pointer; }
.spacer { flex: 1; }
.user-name { color: #fff; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
.sidebar { background: #fff; border-right: 1px solid #e6e6e6; }
.sidebar :deep(.el-menu) { border-right: none; }
.main { background: #f5f7fa; padding: 16px; overflow: auto; }
</style>
