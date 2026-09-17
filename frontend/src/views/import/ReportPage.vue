<template>
  <div v-loading="loading">
    <el-breadcrumb class="crumb">
      <el-breadcrumb-item><router-link to="/import">数据导入</router-link></el-breadcrumb-item>
      <el-breadcrumb-item>导入结果</el-breadcrumb-item>
    </el-breadcrumb>
    <el-steps :active="3" align-center class="steps">
      <el-step title="① 上传" /><el-step title="② 映射与预览" /><el-step title="③ 结果" />
    </el-steps>

    <el-alert v-if="report?.batch?.status === 'failed'" type="error" :closable="false"
              title="批次写入失败，已整体回滚（无半批数据）。可返回修改后重试。" class="block" />

    <div class="cards block" v-if="report">
      <el-card shadow="never"><div class="stat success">{{ report.summary.success }}</div><div class="stat-label">成功</div></el-card>
      <el-card shadow="never"><div class="stat">{{ report.summary.skipped }}</div><div class="stat-label">跳过</div></el-card>
      <el-card shadow="never"><div class="stat danger">{{ report.summary.failed }}</div><div class="stat-label">失败</div></el-card>
      <el-card shadow="never"><div class="stat warn">{{ report.summary.needs_review }}</div><div class="stat-label">待确认</div></el-card>
    </div>

    <el-card shadow="never">
      <div class="row" style="margin-bottom: 10px">
        <el-select v-model="statusFilter" placeholder="全部状态" clearable size="small" style="width: 140px">
          <el-option v-for="(cfg, key) in rowMap" :key="key" :label="cfg.label" :value="key" />
        </el-select>
      </div>
      <el-table :data="filteredItems" size="small" max-height="420">
        <el-table-column prop="file_name" label="文件" min-width="180" show-overflow-tooltip />
        <el-table-column prop="sheet_name" label="工作表" width="130" />
        <el-table-column prop="row_no" label="行号" width="70" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="rowMap[row.status]?.tag || 'info'" size="small">{{ rowMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="生成报价" width="110">
          <template #default="{ row }">
            <router-link v-if="row.quote_ids?.length" :to="`/quotes/${row.quote_ids[0]}`">{{ row.quote_ids.length }} 条</router-link>
            <span v-else>0 条</span>
          </template>
        </el-table-column>
        <el-table-column label="原因" min-width="220">
          <template #default="{ row }">
            <div v-for="(r, i) in row.reasons" :key="i" class="reason">{{ r }}</div>
            <span v-if="!row.reasons?.length">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="bottom">
      <el-button @click="$router.push(`/batches/${batchId}`)">查看批次详情</el-button>
      <div>
        <el-button type="primary" @click="$router.push('/import')">继续导入下一文件</el-button>
        <el-button @click="$router.push('/search')">去搜索页看看</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getReport } from '../../api/imports'
import { ROW_STATUS_MAP } from '../../utils/format'

const route = useRoute()
const batchId = computed(() => route.params.batchId as string)
const loading = ref(true)
const report = ref<any>(null)
const statusFilter = ref()
const rowMap = ROW_STATUS_MAP

const filteredItems = computed(() => {
  const items = report.value?.items || []
  return statusFilter.value ? items.filter((i: any) => i.status === statusFilter.value) : items
})

onMounted(async () => {
  try {
    report.value = await getReport(batchId.value)
  } finally { loading.value = false }
})
</script>

<style scoped>
.crumb { margin-bottom: 14px; }
.steps { margin-bottom: 18px; }
.block { margin-bottom: 14px; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.cards :deep(.el-card__body) { padding: 18px 12px; }
.stat { font-size: 34px; font-weight: 700; text-align: center; font-variant-numeric: tabular-nums; }
.stat.success { color: #16a34a; } .stat.danger { color: #ef4444; } .stat.warn { color: #f59e0b; }
.stat-label { text-align: center; color: #64748b; font-size: 13px; margin-top: 2px; }
.row { display: flex; align-items: center; }
.reason { font-size: 12px; color: #94a3b8; }
.bottom { display: flex; justify-content: space-between; }
</style>
