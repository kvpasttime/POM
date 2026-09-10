<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2 class="title">POM 历史采购报价查询系统</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0" @keyup.enter="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="账号" data-testid="username" autofocus>
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.remember">记住账号</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%" :loading="loading" :disabled="lockRemaining > 0" @click="submit">
            {{ lockRemaining > 0 ? `已锁定，剩余 ${lockRemaining} 秒` : '登 录' }}
          </el-button>
        </el-form-item>
        <el-alert v-if="errorMsg" :title="errorMsg" type="error" :closable="false" />
      </el-form>
    </el-card>
    <div class="footer">v1.0 · 仅限授权用户使用</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

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
  height: 100vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; background: #f5f7fa;
}
.login-card { width: 400px; padding: 12px 8px; }
.title { text-align: center; color: #303133; margin: 8px 0 24px; font-size: 20px; }
.footer { margin-top: 24px; color: #909399; font-size: 12px; }
</style>
