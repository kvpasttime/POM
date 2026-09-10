<template>
  <div v-loading="loading">
    <el-breadcrumb class="crumb">
      <el-breadcrumb-item><router-link to="/search">报价搜索</router-link></el-breadcrumb-item>
      <el-breadcrumb-item><router-link :to="`/quotes/${quoteId}`">报价详情</router-link></el-breadcrumb-item>
      <el-breadcrumb-item>编辑</el-breadcrumb-item>
    </el-breadcrumb>

    <el-card shadow="never">
      <div class="grid" v-if="data">
        <!-- 左：可编辑表单 -->
        <div>
          <el-divider content-position="left">报价信息</el-divider>
          <el-form label-width="90px" size="small">
            <el-form-item label="金额(元)">
              <el-input-number v-model="form.amount" :min="0" :controls="false" :precision="2" style="width: 180px" />
            </el-form-item>
            <el-form-item label="币种">
              <el-select v-model="form.currency" style="width: 120px">
                <el-option v-for="c in ['CNY','USD','EUR','JPY']" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="是否含税">
              <el-radio-group v-model="form.tax_included">
                <el-radio :value="true">是</el-radio><el-radio :value="false">否</el-radio><el-radio :value="null">未知</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="是否含运">
              <el-radio-group v-model="form.freight_included">
                <el-radio :value="true">是</el-radio><el-radio :value="false">否</el-radio><el-radio :value="null">未知</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="可供数量">
              <el-input-number v-model="form.available_qty" :min="0" :controls="false" style="width: 140px" />
            </el-form-item>
            <el-form-item label="报价日期">
              <el-date-picker v-model="form.quote_date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 150px">
                <el-option v-for="(cfg, key) in editableStatusMap" :key="key" :label="cfg.label" :value="key" />
              </el-select>
            </el-form-item>
            <el-form-item label="报价备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>

          <el-divider content-position="left">修改原因（必填，将记入修订记录）</el-divider>
          <el-input v-model="reason" type="textarea" :rows="2" placeholder="请填写修改原因（R-MNT-02）" />
          <div class="actions">
            <el-button @click="cancel">取消</el-button>
            <el-button type="primary" :disabled="!reason.trim() || !dirty" @click="save">保存修改</el-button>
          </div>
        </div>

        <!-- 右：原始内容对照（只读，R-IMP-26） -->
        <div>
          <el-divider content-position="left">原始行快照（不可编辑）</el-divider>
          <div class="meta">
            文件: {{ data.source.file_name }} · 工作表: {{ data.source.sheet_name }} · 行号: {{ data.source.row_no }}
          </div>
          <pre class="raw-cells">{{ JSON.stringify(data.source.raw_cells, null, 2) }}</pre>
          <el-alert type="info" :closable="false" title="结构化修改不会改动以上原始内容（R-IMP-26）" />
          <template v-if="revisions.length">
            <div class="meta" style="margin-top: 12px">最近修订</div>
            <div v-for="r in revisions.slice(0, 5)" :key="r.id" class="rev">
              {{ fmtDateTime(r.changed_at) }} {{ r.changed_by_name }}：{{ r.field }} {{ r.old_value }}→{{ r.new_value }}（{{ r.reason }}）
            </div>
          </template>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { quoteDetail, quoteRevisions, patchQuote } from '../../api/quote'
import { fmtDateTime, QUOTE_STATUS_MAP } from '../../utils/format'

const route = useRoute()
const router = useRouter()
const quoteId = computed(() => route.params.id as string)
const loading = ref(true)
const data = ref<any>(null)
const revisions = ref<any[]>([])
const reason = ref('')
const statusMap = QUOTE_STATUS_MAP
const editableStatusMap: Record<string, { label: string; tag: string }> = Object.fromEntries(
  Object.entries(QUOTE_STATUS_MAP).filter(([k]) => k !== 'deleted'),
)

const form = reactive<any>({})
const original = reactive<any>({})
const dirty = computed(() => Object.keys(form).some((k) => form[k] !== original[k]))

async function load() {
  loading.value = true
  try {
    data.value = await quoteDetail(quoteId.value)
    const q = data.value.quote
    Object.assign(form, {
      amount: q.amount, currency: q.currency, tax_included: q.tax_included,
      freight_included: q.freight_included, available_qty: q.available_qty,
      quote_date: q.quote_date, status: q.status, remark: q.remark,
    })
    Object.assign(original, JSON.parse(JSON.stringify(form)))
    try { revisions.value = (await quoteRevisions(quoteId.value)).items } catch { revisions.value = [] }
  } finally { loading.value = false }
}

async function save() {
  const fields: Record<string, unknown> = {}
  Object.keys(form).forEach((k) => {
    if (form[k] !== original[k]) fields[k] = form[k]
  })
  try {
    await patchQuote(quoteId.value, { fields, reason: reason.value.trim(), version: data.value.version })
    ElMessage.success('已保存，修订记录已更新')
    router.push(`/quotes/${quoteId.value}`)
  } catch (e: any) {
    if (e?.code === 40404) ElMessage.warning('该记录已被他人修改，请刷新后重试')
  }
}

async function cancel() {
  if (dirty.value) {
    await ElMessageBox.confirm('有未保存的修改，确认放弃？', '提示', { type: 'warning' })
  }
  router.push(`/quotes/${quoteId.value}`)
}

onMounted(load)
</script>

<style scoped>
.crumb { margin-bottom: 12px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 1200px) { .grid { grid-template-columns: 1fr; } }
.actions { margin-top: 12px; display: flex; gap: 8px; justify-content: flex-end; }
.meta { color: #606266; font-size: 13px; margin-bottom: 8px; }
.raw-cells {
  background: #f8f8f8; border: 1px solid #ebeef5; border-radius: 4px;
  padding: 10px; font-size: 12px; max-height: 320px; overflow: auto; white-space: pre-wrap;
  margin-bottom: 10px;
}
.rev { font-size: 12px; color: #606266; margin-bottom: 4px; }
</style>
