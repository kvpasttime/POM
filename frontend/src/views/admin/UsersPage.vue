<template>
  <div>
    <el-breadcrumb class="crumb"><el-breadcrumb-item>用户管理</el-breadcrumb-item></el-breadcrumb>
    <el-card shadow="never" class="block">
      <div class="row">
        <el-input v-model="filters.keyword" placeholder="账号 / 姓名" clearable style="width: 200px" @keyup.enter="load" />
        <el-select v-model="filters.role" placeholder="角色" clearable style="width: 140px" @change="load">
          <el-option label="普通用户" value="user" />
          <el-option label="数据维护员" value="maintainer" />
          <el-option label="系统管理员" value="admin" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px" @change="load">
          <el-option label="启用" value="enabled" /><el-option label="停用" value="disabled" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <div class="spacer" />
        <el-button type="primary" @click="createDialog = true">+ 新建用户</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column prop="username" label="账号" width="130" />
        <el-table-column prop="display_name" label="姓名" width="120" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'enabled' ? 'success' : 'danger'" size="small">
              {{ row.status === 'enabled' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ fmtDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最近登录" width="160">
          <template #default="{ row }">{{ fmtDateTime(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="220">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="doReset(row)">重置密码</el-button>
            <el-button v-if="row.status === 'enabled'" link type="danger" @click="toggle(row, 'disabled')">停用</el-button>
            <el-button v-else link type="success" @click="toggle(row, 'enabled')">启用</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                       layout="total, prev, pager, next" @current-change="load" />
      </div>
    </el-card>

    <!-- 新建 -->
    <el-dialog v-model="createDialog" title="新建用户" width="420px">
      <el-form label-width="70px">
        <el-form-item label="账号"><el-input v-model="createForm.username" maxlength="32" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="createForm.display_name" maxlength="64" /></el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="createForm.role">
            <el-radio value="user">普通用户</el-radio>
            <el-radio value="maintainer">数据维护员</el-radio>
            <el-radio value="admin">系统管理员</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑 -->
    <el-dialog v-model="editDialog" title="编辑用户" width="420px">
      <el-form label-width="70px">
        <el-form-item label="账号"><el-input :model-value="editTarget?.username" disabled /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="editForm.display_name" /></el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="editForm.role">
            <el-radio value="user">普通用户</el-radio>
            <el-radio value="maintainer">数据维护员</el-radio>
            <el-radio value="admin">系统管理员</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" @click="doEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 一次性密码 -->
    <el-dialog v-model="pwdDialog" title="初始密码（仅显示一次）" width="380px" :close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
      <div class="pwd">{{ oneTimePwd }}</div>
      <el-alert type="warning" :closable="false" title="请立即告知用户，关闭后不可再次查看" />
      <template #footer>
        <el-button @click="copyPwd">复制</el-button>
        <el-button type="primary" @click="pwdDialog = false">我已保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, createUser, updateUser, resetPassword, UserItem } from '../../api/user'
import { fmtDateTime } from '../../utils/format'

const loading = ref(false)
const rows = ref<UserItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filters = reactive<{ keyword?: string; role?: string; status?: string }>({})

const createDialog = ref(false)
const createForm = reactive({ username: '', display_name: '', role: 'user' })
const editDialog = ref(false)
const editTarget = ref<UserItem | null>(null)
const editForm = reactive({ display_name: '', role: 'user' })
const pwdDialog = ref(false)
const oneTimePwd = ref('')

const roleLabel = (r: string) => ({ user: '普通用户', maintainer: '数据维护员', admin: '系统管理员' }[r] || r)

async function load() {
  loading.value = true
  try {
    const data = await listUsers({ ...filters, page: page.value, pageSize })
    rows.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function reset() {
  filters.keyword = undefined
  filters.role = undefined
  filters.status = undefined
  load()
}

async function doCreate() {
  try {
    const data = await createUser({ ...createForm })
    oneTimePwd.value = data.initial_password
    pwdDialog.value = true
    createDialog.value = false
    createForm.username = ''
    createForm.display_name = ''
    load()
  } catch { /* 错误已全局提示 */ }
}

function openEdit(row: UserItem) {
  editTarget.value = row
  editForm.display_name = row.display_name
  editForm.role = row.role
  editDialog.value = true
}

async function doEdit() {
  if (!editTarget.value) return
  await updateUser(editTarget.value.id, {
    display_name: editForm.display_name, role: editForm.role, version: editTarget.value.version,
  })
  ElMessage.success('已保存')
  editDialog.value = false
  load()
}

async function doReset(row: UserItem) {
  await ElMessageBox.confirm(`确认重置 ${row.username} 的密码？该用户全部会话将立即失效。`, '重置确认', { type: 'warning' })
  const data = await resetPassword(row.id)
  oneTimePwd.value = data.new_password
  pwdDialog.value = true
  load()
}

async function toggle(row: UserItem, status: string) {
  if (status === 'disabled') {
    await ElMessageBox.confirm(`确认停用 ${row.username}？该用户所有会话将立即失效。`, '停用确认', { type: 'warning' })
  }
  await updateUser(row.id, { status, version: row.version })
  ElMessage.success(status === 'disabled' ? '已停用' : '已启用')
  load()
}

async function copyPwd() {
  await navigator.clipboard.writeText(oneTimePwd.value)
  ElMessage.success('已复制')
}

onMounted(load)
</script>

<style scoped>
.crumb { margin-bottom: 12px; }
.block { margin-bottom: 12px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.spacer { flex: 1; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.pwd { font-size: 22px; font-weight: 600; text-align: center; margin-bottom: 12px; letter-spacing: 2px; }
</style>
