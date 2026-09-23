<template>
  <div class="login-page">
    <div class="deco deco-1" />
    <div class="deco deco-2" />
    <el-card class="login-card">
      <div class="logo-row">
        <div class="logo">P</div>
        <div>
          <h2 class="title">POM 采购报价库</h2>
          <p class="subtitle">历史采购报价查询系统</p>
        </div>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0" @keyup.enter="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="账号" size="large" autofocus>
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" size="large">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <div class="aux-row">
          <el-checkbox v-model="form.remember">记住账号</el-checkbox>
        </div>
        <el-form-item>
          <el-button type="primary" size="large" style="width: 100%" :loading="loading"
                     :disabled="lockRemaining > 0" @click="submit">
            <span v-if="lockRemaining > 0">已锁定，剩余 {{ lockRemaining }} 秒</span>
            <span v-else>登 录</span>
          </el-button>
        </el-form-item>
        <el-alert v-if="errorMsg" :title="errorMsg" type="error" :closable="false" />
      </el-form>
      <div class="footer">v{{ APP_VERSION }} · 仅限授权用户使用</div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { APP_VERSION } from '../utils/format'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const formRef = ref()
const loading = ref(false)
const errorMsg = ref('')
const lockRemaining = ref(0)
let timer: number | undefined

const form = reactive({
  username: localStorage.getItem('pom_remember_username') || '',
  password: '',
  remember: !!localStorage.getItem('pom_remember_username'),
})

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

onMounted(() => {
  if (auth.token) router.replace('/search')
})
onUnmounted(() => window.clearInterval(timer))

function startLockCountdown(seconds: number) {
  lockRemaining.value = seconds
  timer = window.setInterval(() => {
    lockRemaining.value -= 1
    if (lockRemaining.value <= 0) window.clearInterval(timer)
  }, 1000)
}

async function submit() {
  await formRef.value?.validate().catch(() => Promise.reject())
  loading.value = true
  errorMsg.value = ''
  try {
    await auth.login(form.username.trim(), form.password, form.remember)
    const redirect = (route.query.redirect as string) || '/search'
    router.replace(redirect)
  } catch (e: any) {
    errorMsg.value = e?.message || '登录失败'
    if (e?.extra?.retry_after) startLockCountdown(e.extra.retry_after)
    form.password = ''
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 40%, #f5f3ff 100%);
  position: relative;
  overflow: hidden;
}
.deco {
  position: absolute; border-radius: 50%;
  filter: blur(80px); opacity: 0.5; pointer-events: none;
}
.deco-1 {
  width: 480px; height: 480px; left: -120px; top: -140px;
  background: radial-gradient(circle, #818cf8 0%, transparent 70%);
}
.deco-2 {
  width: 520px; height: 520px; right: -160px; bottom: -180px;
  background: radial-gradient(circle, #c4b5fd 0%, transparent 70%);
}
.login-card {
  width: 400px;
  padding: 10px 6px 4px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.14);
}
.logo-row { display: flex; align-items: center; gap: 14px; margin: 10px 6px 24px; }
.logo {
  width: 48px; height: 48px; border-radius: 14px;
  background: linear-gradient(135deg, #4f46e5 0%, #8b5cf6 100%);
  color: #fff; font-weight: 800; font-size: 24px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 20px rgba(79, 70, 229, 0.4);
}
.title { margin: 0; font-size: 19px; color: #0f172a; line-height: 1.25; }
.subtitle { margin: 2px 0 0; font-size: 12px; color: #94a3b8; }
.aux-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.footer { text-align: center; color: #94a3b8; font-size: 12px; margin-top: 14px; }
</style>
