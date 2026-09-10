<template>
  <div v-loading="loading">
    <el-breadcrumb class="crumb">
      <el-breadcrumb-item><router-link to="/import">数据导入</router-link></el-breadcrumb-item>
      <el-breadcrumb-item>映射与预览</el-breadcrumb-item>
    </el-breadcrumb>
    <el-steps :active="2" align-center class="steps">
      <el-step title="① 上传" /><el-step title="② 映射与预览" /><el-step title="③ 结果" />
    </el-steps>

    <el-card shadow="never" class="block">
      <div class="row">
        <span>文件：</span>
        <el-select v-model="currentFileId" style="width: 320px" @change="loadPreview">
          <el-option v-for="f in passedFiles" :key="f.file_id" :label="f.filename" :value="f.file_id" />
        </el-select>
        <el-select v-model="sheetName" style="width: 200px" @change="loadPreview">
          <el-option v-for="s in sheets" :key="s.name" :label="`${s.name}（${s.row_count}行）`" :value="s.name" />
        </el-select>
        <span>表头行：</span>
        <el-input-number v-model="headerRow" :min="1" size="small" placeholder="自动" @change="loadPreview" />
        <el-tag v-if="preview?.is_template" type="success" size="small">已识别标准模板</el-tag>
      </div>
      <el-alert v-if="preview?.shift_detected" type="warning" :closable="false"
                :title="preview?.shift_message || '检测到列位移'" class="shift" />
    </el-card>

    <el-card shadow="never" class="block">
      <div class="row" style="justify-content: space-between">
        <b>字段映射</b>
        <div class="row" style="gap: 8px">
          <el-select v-model="applyTemplateId" placeholder="应用已有模板" size="small" style="width: 200px" @change="applyTemplate">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
          <el-button size="small" @click="doSaveTemplate">保存为映射模板</el-button>
        </div>
      </div>
      <el-table :data="mappingRows" size="small" max-height="320">
        <el-table-column prop="standard_label" label="标准字段" width="160" />
        <el-table-column label="源列" width="220">
          <template #default="{ row }">
            <el-select v-model="row.source_column" clearable size="small" @change="reparse">
              <el-option v-for="(h, i) in headerTexts" :key="i" :label="`${i + 1}. ${h || '(空)'}`" :value="i" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="sample_value" label="示例值(首行)" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.source_column != null ? 'success' : 'info'" size="small">
              {{ row.source_column != null ? '已映射' : '未映射' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never" class="block">
      <div class="row" style="justify-content: space-between">
        <b>行级预览
          <el-tag size="small" type="success" style="margin-left: 8px">正常 {{ preview?.summary?.ok || 0 }}</el-tag>
          <el-tag size="small" type="warning" style="margin-left: 4px">警告 {{ preview?.summary?.warn || 0 }}</el-tag>
          <el-tag size="small" type="danger" style="margin-left: 4px">错误 {{ preview?.summary?.error || 0 }}</el-tag>
          <el-tag size="small" type="info" style="margin-left: 4px">重复 {{ preview?.summary?.duplicate || 0 }}</el-tag>
        </b>
        <div class="row" style="gap: 8px">
          <el-checkbox v-model="onlyAbnormal">仅看异常</el-checkbox>
          <el-switch v-model="skipErrorRows" active-text="跳过错误行" />
        </div>
      </div>
      <el-table :data="visibleRows" size="small" max-height="360">
        <el-table-column prop="row_no" label="行号" width="70" />
        <el-table-column prop="material_name" label="物料名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="material_code" label="编码" width="100" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="rowTag(row.status)" size="small">{{ rowLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quote_count" label="拆分报价数" width="95" />
        <el-table-column label="预览(金额/供应商/状态)" min-width="240">
          <template #default="{ row }">
            <div v-for="(p, i) in row.preview" :key="i" class="qline">
              {{ p.amount ?? '—' }} / {{ p.supplier || '待确认' }} / {{ p.status }}
            </div>
            <span v-if="!row.preview?.length">—</span>
          </template>
        </el-table-column>
        <el-table-column label="原因" min-width="200">
          <template #default="{ row }">
            <span v-if="!row.reasons?.length">—</span>
            <div v-for="(r, i) in row.reasons" :key="i" class="reason">{{ r }}</div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="bottom">
      <el-button @click="$router.push('/import')">上一步</el-button>
      <div class="row" style="gap: 8px">
        <el-button :loading="loading" @click="loadPreview">重新解析</el-button>
        <el-button type="primary" :disabled="!canCommit" @click="doCommit">确认导入</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getBatch, getPreview, updatePreview, commitImport, listTemplates, saveTemplate as saveTemplateApi } from '../../api/imports'

const route = useRoute()
const router = useRouter()
const batchId = computed(() => route.params.batchId as string)
const loading = ref(false)
const passedFiles = ref<any[]>([])
const currentFileId = ref<number>()
const sheets = ref<any[]>([])
const sheetName = ref<string | undefined>(undefined)
const headerRow = ref<number | undefined>(undefined)
const preview = ref<any>(null)
const mappingRows = ref<any[]>([])
const onlyAbnormal = ref(false)
const skipErrorRows = ref(false)
const templates = ref<any[]>([])
const applyTemplateId = ref()

const FIELD_LABELS: Record<string, string> = {
  row_no: '行号', quote_row_no: '报价行编号', material_code: '物料编码', material_name: '物料名称',
  tech_params: '技术参数', spec_model: '规格型号', part_no: '零件号/图号', material_text: '材质',
  brand: '品牌', origin_type: '进口/国产', unit: '单位', usage_unit: '使用单位', receiver: '接收人',
  requirement_date: '需求日期', remark: '备注', quantity: '需求数量', supplier_spec_model: '供应商规格型号',
  supplier_material: '供应商材质', supplier_tech_params: '供应商技术参数', supplier_name: '供应商',
  delivery_date: '交货日期', transport_mode: '运输方式', available_qty: '可供数量',
  amount: '含税单价', quote_remark: '报价备注',
}

const headerTexts = computed(() => preview.value?.header_texts || [])

const mappingRowsBase = computed(() => {
  const ms = preview.value?.mappings || []
  const firstRow = preview.value?.rows?.[0]
  return ms.map((m: any) => ({
    standard_field: m.standard_field,
    standard_label: FIELD_LABELS[m.standard_field] || m.standard_field,
    source_column: m.source_column,
    sample_value: firstRow?.preview?.length ? '—' : '—',
  }))
})

const visibleRows = computed(() => {
  const rows = preview.value?.rows || []
  if (!onlyAbnormal.value) return rows
  return rows.filter((r: any) => r.status !== 'ok')
})

const canCommit = computed(() => {
  const s = preview.value?.summary
  if (!s) return false
  return s.error === 0 || skipErrorRows.value
})

const rowLabel = (s: string) => ({ ok: '正常', warn: '警告', error: '错误', duplicate: '重复' }[s] || s)
const rowTag = (s: string) => ({ ok: 'success', warn: 'warning', error: 'danger', duplicate: 'info' }[s] || 'info')

function syncMappingRows() {
  // 编辑期间保留用户修改
  if (!mappingRows.value.length) {
    mappingRows.value = mappingRowsBase.value
  }
}

function currentMappings() {
  return mappingRows.value
    .filter((r) => r.source_column !== null && r.source_column !== undefined)
    .map((r) => ({ standard_field: r.standard_field, source_column: r.source_column }))
}

async function loadPreview() {
  if (!currentFileId.value) return
  loading.value = true
  try {
    const data = await getPreview(batchId.value, currentFileId.value, sheetName.value, headerRow.value)
    preview.value = data
    sheetName.value = data.sheet_name
    headerRow.value = data.header_row
    mappingRows.value = data.mappings.map((m: any) => ({
      standard_field: m.standard_field,
      standard_label: FIELD_LABELS[m.standard_field] || m.standard_field,
      source_column: m.source_column,
    }))
  } finally { loading.value = false }
}

async function reparse() {
  if (!currentFileId.value) return
  loading.value = true
  try {
    const data = await updatePreview(batchId.value, {
      file_id: currentFileId.value, sheet_name: sheetName.value,
      header_row: headerRow.value, mappings: currentMappings(),
      skip_error_rows: skipErrorRows.value,
    })
    preview.value = data
  } finally { loading.value = false }
}

async function applyTemplate() {
  const t = templates.value.find((x) => x.id === applyTemplateId.value)
  if (!t) return
  mappingRows.value = mappingRows.value.map((r) => {
    const found = (t.mappings || []).find((m: any) => m.standard_field === r.standard_field)
    return found ? { ...r, source_column: found.source_column } : r
  })
  await reparse()
}

async function doSaveTemplate() {
  const { value } = await ElMessageBox.prompt('模板名称', '保存映射模板', { inputValue: '' })
  await saveTemplateApi({
    name: value.trim(), header_fingerprint: preview.value.header_fingerprint,
    sheet_hint: sheetName.value, mappings: currentMappings(),
  })
  ElMessage.success('模板已保存')
  templates.value = (await listTemplates()).items
}

async function doCommit() {
  loading.value = true
  try {
    await commitImport(batchId.value, {
      commit_token: preview.value.commit_token,
      file_commits: [{
        file_id: currentFileId.value, sheet_name: sheetName.value,
        header_row: headerRow.value, mappings: currentMappings(),
        skip_error_rows: skipErrorRows.value,
      }],
    })
    router.push(`/import/${batchId.value}/report`)
  } finally { loading.value = false }
}

onMounted(async () => {
  const batch = await getBatch(batchId.value)
  passedFiles.value = batch.files.filter((f: any) => f.check_status === 'passed')
  // 汇总各文件的 sheets（来自详情 row_results 之外，直接用 preview 接口补）
  if (passedFiles.value.length) {
    currentFileId.value = passedFiles.value[0].file_id
    await loadPreview()
    sheets.value = (preview.value.sheet_names || []).map((n: string) => ({ name: n, row_count: '—' }))
    try { templates.value = (await listTemplates()).items } catch { templates.value = [] }
  } else {
    ElMessage.warning('没有通过校验的文件')
  }
})
</script>

<style scoped>
.crumb { margin-bottom: 12px; }
.steps { margin-bottom: 16px; }
.block { margin-bottom: 12px; }
.row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.shift { margin-top: 10px; }
.qline { font-size: 12px; color: #606266; }
.reason { font-size: 12px; color: #e6a23c; }
.bottom { display: flex; justify-content: space-between; }
</style>
