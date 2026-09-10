<template>
  <div v-loading="loading">
    <el-breadcrumb class="crumb">
      <el-breadcrumb-item><router-link to="/batches">导入批次</router-link></el-breadcrumb-item>
      <el-breadcrumb-item>{{ batch?.batch_no }}</el-breadcrumb-item>
    </el-breadcrumb>

    <el-card shadow="never" class="block">
      <el-descriptions :column="4" border>
        <el-descriptions-item label="批次号">{{ batch?.batch_no }}</el-descriptions-item>
        <el-descriptions-item label="上传人">{{ batch?.uploaded_by_name }}</el-descriptions-item>
        <el-descriptions-item label="上传时间">{{ fmtDateTime(batch?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusMap[batch?.status]?.tag" size="small">{{ statusMap[batch?.status]?.label }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="block">
      <div class="title">源文件</div>
      <el-table :data="batch?.files || []" size="small">
        <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="sha256" label="哈希" width="100" />
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ (row.size / 1024).toFixed(1) }}KB</template>
        </el-table-column>
        <el-table-column prop="check_status" label="校验" width="90" />
        <el-table-column label="" width="130">
          <template #default="{ row }">
            <el-button v-if="row.check_status === 'passed'" link type="primary" @click="download(row.file_id)">
              下载原始文件
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <div class="title">行级明细</div>
      <el-table :data="batch?.row_results || []" size="small" max-height="420">
        <el-table-column prop="file_name" label="文件" min-width="160" show-overflow-tooltip />
        <el-table-column prop="sheet_name" label="工作表" width="120" />
        <el-table-column prop="row_no" label="行号" width="70" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="rowMap[row.status]?.tag || 'info'" size="small">{{ rowMap[row.status]?.label || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="生成报价" width="110">
          <template #default="{ row }">
            <router-link v-if="row.quote_ids?.length" :to="`/quotes/${row.quote_ids[0]}`">{{ row.quote_count }} 条</router-link>
            <span v-else>0 条</span>
          </template>
        </el-table-column>
        <el-table-column label="当前报价状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.quote_statuses && Object.values(row.quote_statuses).includes('deleted')"
                    type="danger" size="small">已删除</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="原因" min-width="200">
          <template #default="{ row }">
            <div v-for="(r, i) in row.reasons" :key="i" class="reason">{{ r }}</div>
            <span v-if="!row.reasons?.length">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getBatch } from '../../api/imports'
import { fmtDateTime, BATCH_STATUS_MAP, ROW_STATUS_MAP } from '../../utils/format'
import { fileDownloadUrl } from '../../api/quote'

const route = useRoute()
const batchId = computed(() => route.params.id as string)
const loading = ref(true)
const batch = ref<any>(null)
const statusMap = BATCH_STATUS_MAP
const rowMap = ROW_STATUS_MAP

function download(fileId: number) {
  window.open(fileDownloadUrl(fileId), '_blank')
}

onMounted(async () => {
  try { batch.value = await getBatch(batchId.value) } finally { loading.value = false }
})
</script>

<style scoped>
.crumb { margin-bottom: 12px; }
.block { margin-bottom: 12px; }
.title { font-weight: 600; margin-bottom: 10px; }
.reason { font-size: 12px; color: #909399; }
</style>
