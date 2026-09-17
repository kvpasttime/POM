<template>
  <div>
    <el-breadcrumb class="crumb">
      <el-breadcrumb-item>数据导入</el-breadcrumb-item>
    </el-breadcrumb>
    <el-steps :active="1" align-center class="steps">
      <el-step title="① 上传" /><el-step title="② 映射与预览" /><el-step title="③ 结果" />
    </el-steps>

    <el-card shadow="never">
      <el-upload drag multiple :auto-upload="false" :file-list="fileList" :on-change="onFileChange"
                 accept=".xls,.xlsx" :show-file-list="false">
        <el-icon size="42"><UploadFilled /></el-icon>
        <div class="el-upload__text">点击或拖拽文件到此处上传</div>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xls / .xlsx，单文件 ≤ {{ maxMb }}MB</div>
        </template>
      </el-upload>
      <div style="margin-top: 12px">
        <el-button type="primary" :loading="uploading" :disabled="!fileList.length" @click="doUpload">上传并校验</el-button>
      </div>
    </el-card>

    <el-card shadow="never" v-if="results.length">
      <el-table :data="results">
        <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ (row.size / 1024).toFixed(1) }}KB</template>
        </el-table-column>
        <el-table-column prop="sha256" label="哈希" width="100" />
        <el-table-column label="校验结果" min-width="180">
          <template #default="{ row }">{{ row.check_message || '通过' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.check_status === 'passed' ? 'success' : row.check_status === 'duplicate' ? 'warning' : 'danger'" size="small">
              {{ ({ passed: '待映射', failed: '失败', duplicate: '重复' } as Record<string,string>)[row.check_status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="" width="130">
          <template #default="{ row }">
            <el-button v-if="row.check_status === 'duplicate' && row.duplicate_of_batch_id" link type="primary"
                       @click="$router.push(`/batches/${row.duplicate_of_batch_id}`)">查看原批次</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 12px; text-align: right">
        <el-button type="primary" :disabled="!batchId" @click="$router.push(`/import/${batchId}/map`)">开始映射</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { uploadFiles } from '../../api/imports'

const router = useRouter()
const maxMb = 20
const fileList = ref<any[]>([])
const results = ref<any[]>([])
const uploading = ref(false)
const batchId = ref<number | null>(null)

function onFileChange(file: any, list: any[]) {
  fileList.value = list.map((f) => f.raw).filter(Boolean)
  results.value = []
  batchId.value = null
}

async function doUpload() {
  uploading.value = true
  try {
    const data = await uploadFiles(fileList.value)
    batchId.value = data.batch_id
    results.value = data.files
    const failed = data.files.filter((f: any) => f.check_status === 'failed').length
    if (failed > 0) ElMessage.warning(`${failed} 个文件校验失败，不影响其余文件继续处理`)
  } finally { uploading.value = false }
}
</script>

<style scoped>
.crumb { margin-bottom: 14px; }
.steps { margin-bottom: 18px; }
:deep(.el-upload-dragger) {
  border-radius: 14px;
  padding: 34px 20px;
  border: 1.5px dashed #c7d0dd;
  background: #f8fafc;
  transition: all 0.2s ease;
}
:deep(.el-upload-dragger:hover) {
  border-color: var(--el-color-primary);
  background: #eef2ff;
}
:deep(.el-upload-dragger .el-icon) { color: var(--el-color-primary); }
</style>
