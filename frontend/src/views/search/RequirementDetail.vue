<template>
  <div v-loading="loading">
    <el-breadcrumb class="crumb">
      <el-breadcrumb-item><router-link to="/search">报价搜索</router-link></el-breadcrumb-item>
      <el-breadcrumb-item>需求详情 #{{ requirementId }}</el-breadcrumb-item>
    </el-breadcrumb>

    <el-card shadow="never" class="summary">
      <div class="summary-main">
        <span class="name">{{ data?.material?.name || '—' }}</span>
        <span class="sep">·</span><span>{{ data?.material?.spec_model || '—' }}</span>
        <span class="sep">·</span><span class="unit">{{ data?.requirement?.unit || '—' }}</span>
        <span class="sep">·</span><span>{{ fmtDate(data?.requirement?.requirement_date) }}</span>
      </div>
      <div class="summary-tags">
        <el-tag type="warning" size="small">无报价</el-tag>
        <el-tag size="small" type="info">该需求暂无供应商报价，仅有需求记录</el-tag>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-tabs>
        <el-tab-pane label="物料与需求">
          <el-descriptions :column="2" border v-if="data?.material">
            <el-descriptions-item label="物料编码">{{ data.material.code || '—' }}</el-descriptions-item>
            <el-descriptions-item label="物料名称">{{ data.material.name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="分类">{{ data.material.category || '—' }}</el-descriptions-item>
            <el-descriptions-item label="规格型号">{{ data.material.spec_model || '—' }}</el-descriptions-item>
            <el-descriptions-item label="技术参数" :span="2">{{ data.material.tech_params || '—' }}</el-descriptions-item>
            <el-descriptions-item label="品牌">{{ data.material.brand || '—' }}</el-descriptions-item>
            <el-descriptions-item label="单位">{{ data.material.unit || '—' }}</el-descriptions-item>
            <el-descriptions-item label="物料描述原文" :span="2">{{ data.material.name_raw || '—' }}</el-descriptions-item>
          </el-descriptions>
          <el-descriptions :column="2" border class="sub" v-if="data?.requirement">
            <el-descriptions-item label="需求数量">{{ data.requirement.quantity ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="使用单位">{{ data.requirement.unit || '—' }}</el-descriptions-item>
            <el-descriptions-item label="需求日期">{{ fmtDate(data.requirement.requirement_date) }}</el-descriptions-item>
            <el-descriptions-item label="接收人">{{ data.requirement.receiver || '—' }}</el-descriptions-item>
            <el-descriptions-item label="报价行编号">{{ data.requirement.quote_row_no || '—' }}</el-descriptions-item>
            <el-descriptions-item label="需求备注">{{ data.requirement.remark || '—' }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="原始来源">
          <el-descriptions :column="2" border v-if="data?.source">
            <el-descriptions-item label="来源文件">{{ data.source.file_name }}</el-descriptions-item>
            <el-descriptions-item label="工作表">{{ data.source.sheet_name }}</el-descriptions-item>
            <el-descriptions-item label="行号">第 {{ data.source.row_no }} 行</el-descriptions-item>
            <el-descriptions-item label="导入批次">{{ data.source.batch_no }}</el-descriptions-item>
            <el-descriptions-item label="上传人">{{ data.source.uploaded_by || '—' }}</el-descriptions-item>
            <el-descriptions-item label="上传时间">{{ fmtDateTime(data.source.uploaded_at) }}</el-descriptions-item>
          </el-descriptions>
          <div class="raw-title">原始文本（只读快照，逐单元格）</div>
          <pre class="raw-cells">{{ JSON.stringify(data?.source?.raw_cells || {}, null, 2) }}</pre>
          <el-button v-if="data?.source?.file_id" size="small" @click="downloadFile">
            <el-icon><Download /></el-icon>&nbsp;下载原始文件
          </el-button>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Download } from '@element-plus/icons-vue'
import { requirementDetail } from '../../api/quote'
import { fileDownloadUrl } from '../../api/quote'
import { fmtDate, fmtDateTime } from '../../utils/format'

const route = useRoute()
const requirementId = computed(() => route.params.id as string)
const loading = ref(true)
const data = ref<any>(null)

function downloadFile() {
  window.open(fileDownloadUrl(data.value.source.file_id), '_blank')
}

onMounted(async () => {
  try { data.value = await requirementDetail(requirementId.value) } finally { loading.value = false }
})
</script>

<style scoped>
.crumb { margin-bottom: 12px; }
.summary { margin-bottom: 12px; }
.summary-main { font-size: 16px; display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
.summary-main .name { font-weight: 600; font-size: 18px; }
.sep { color: #c0c4cc; }
.summary-tags { margin-top: 10px; display: flex; gap: 8px; }
.sub { margin-top: 12px; }
.raw-title { margin: 12px 0 6px; color: #606266; font-size: 13px; }
.raw-cells {
  background: #f8f8f8; border: 1px solid #ebeef5; border-radius: 4px;
  padding: 10px; font-size: 12px; max-height: 260px; overflow: auto; white-space: pre-wrap;
  margin-bottom: 10px;
}
</style>
