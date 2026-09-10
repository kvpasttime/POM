<template>
  <div>
    <el-breadcrumb class="crumb"><el-breadcrumb-item>导入批次</el-breadcrumb-item></el-breadcrumb>
    <el-card shadow="never" class="block">
      <div class="row">
        <el-input v-model="filters.keyword" placeholder="批次号 / 文件名" clearable style="width: 220px" @keyup.enter="load" />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px" @change="load">
          <el-option v-for="(cfg, key) in statusMap" :key="key" :label="cfg.label" :value="key" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </div>
    </el-card>
    <el-card shadow="never">
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column label="批次号" width="150">
          <template #default="{ row }">
            <router-link :to="`/batches/${row.id}`">{{ row.batch_no }}</router-link>
          </template>
        </el-table-column>
        <el-table-column label="文件数" prop="file_count" width="80" />
        <el-table-column prop="uploaded_by_name" label="上传人" width="110" />
        <el-table-column label="上传时间" width="160">
          <template #default="{ row }">{{ fmtDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="success_count" label="成功" width="70" />
        <el-table-column prop="skipped_count" label="跳过" width="70" />
        <el-table-column prop="failed_count" label="失败" width="70" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.tag" size="small">{{ statusMap[row.status]?.label }}</el-tag>
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
import { listBatches } from '../../api/imports'
import { fmtDateTime, BATCH_STATUS_MAP } from '../../utils/format'

const statusMap = BATCH_STATUS_MAP
const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filters = reactive<{ keyword?: string; status?: string }>({})

async function load() {
  loading.value = true
  try {
    const data = await listBatches({ ...filters, page: page.value, pageSize })
    rows.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

function reset() {
  filters.keyword = undefined
  filters.status = undefined
  load()
}

onMounted(load)
</script>

<style scoped>
.crumb { margin-bottom: 12px; }
.block { margin-bottom: 12px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
</style>
