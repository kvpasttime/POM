<template>
  <div v-loading="loading">
    <el-breadcrumb class="crumb"><el-breadcrumb-item>备份状态</el-breadcrumb-item></el-breadcrumb>
    <el-alert v-if="data?.alert" :type="data.alert.level === 'error' ? 'error' : 'warning'"
              :title="data.alert.message" :closable="false" class="block" />
    <el-card shadow="never">
      <el-table :data="data?.items || []" stripe>
        <el-table-column prop="backup_date" label="备份日期" width="140" />
        <el-table-column prop="type" label="类型" width="130" />
        <el-table-column prop="size" label="大小" width="110" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="artifact_name" label="产物名" min-width="240" />
      </el-table>
      <el-empty v-if="data && !data.items?.length" description="尚未生成备份" />
      <el-alert class="tip" type="info" :closable="false"
                title="恢复操作需按 deploy/backup/RESTORE.md 在服务器执行，本页仅展示状态" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { backupStatus } from '../../api/admin'

const loading = ref(true)
const data = ref<any>(null)

onMounted(async () => {
  try { data.value = await backupStatus() } finally { loading.value = false }
})
</script>

<style scoped>
.crumb { margin-bottom: 12px; }
.block { margin-bottom: 12px; }
.tip { margin-top: 12px; }
</style>
