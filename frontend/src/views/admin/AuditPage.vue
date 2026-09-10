<template>
  <div>
    <el-breadcrumb class="crumb"><el-breadcrumb-item>审计日志</el-breadcrumb-item></el-breadcrumb>
    <el-card shadow="never" class="block">
      <div class="row">
        <el-date-picker v-model="timeRange" type="datetimerange" value-format="YYYY-MM-DDTHH:mm:ss"
                        start-placeholder="开始时间" end-placeholder="结束时间" style="width: 340px" @change="load" />
        <el-select v-model="filters.action" placeholder="动作" clearable filterable style="width: 170px" @change="load">
          <el-option v-for="a in ACTIONS" :key="a" :label="a" :value="a" />
        </el-select>
        <el-select v-model="filters.object_type" placeholder="对象类型" clearable style="width: 130px" @change="load">
          <el-option v-for="t in ['user','quote','import_batch','file','mapping_template']" :key="t" :label="t" :value="t" />
        </el-select>
        <el-input v-model="filters.keyword" placeholder="摘要关键词" clearable style="width: 180px" @keyup.enter="load" />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>
    </el-card>
    <el-card shadow="never">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column label="时间" width="165">
          <template #default="{ row }">{{ fmtDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="actor_name" label="操作人" width="110" />
        <el-table-column prop="action" label="动作" width="150" />
        <el-table-column label="对象" width="150">
          <template #default="{ row }">{{ row.object_type }}{{ row.object_id ? `#${row.object_id}` : '' }}</template>
        </el-table-column>
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">
              {{ row.result === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="220" show-overflow-tooltip />
        <el-table-column type="expand">
          <template #default="{ row }">
            <pre class="detail">{{ JSON.stringify(row.detail, null, 2) }}</pre>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                       layout="total, prev, pager, next" @current-change="load" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { queryAudit } from '../../api/admin'
import { fmtDateTime } from '../../utils/format'

const ACTIONS = ['LOGIN', 'LOGIN_FAILED', 'LOGOUT', 'USER_CREATE', 'USER_DISABLE', 'USER_RESET',
  'IMPORT_UPLOAD', 'IMPORT_COMMIT', 'QUOTE_UPDATE', 'QUOTE_DELETE', 'QUOTE_RESTORE',
  'STATUS_MARK', 'SENSITIVE_VIEW', 'FILE_DOWNLOAD', 'USER_UPDATE']

const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const timeRange = ref<[string, string] | null>(null)
const filters = reactive<{ action?: string; object_type?: string; keyword?: string }>({})

async function load() {
  loading.value = true
  try {
    const data = await queryAudit({
      ...filters,
      time_from: timeRange.value?.[0], time_to: timeRange.value?.[1],
      page: page.value, pageSize,
    })
    rows.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function reset() {
  filters.action = undefined
  filters.object_type = undefined
  filters.keyword = undefined
  timeRange.value = null
  load()
}

onMounted(load)
</script>

<style scoped>
.crumb { margin-bottom: 12px; }
.block { margin-bottom: 12px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.detail { font-size: 12px; background: #f8f8f8; padding: 8px; max-height: 240px; overflow: auto; }
</style>
