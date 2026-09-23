<template>
  <div v-loading="loading">
    <el-breadcrumb class="crumb">
      <el-breadcrumb-item><router-link to="/search">报价搜索</router-link></el-breadcrumb-item>
      <el-breadcrumb-item>报价详情 #{{ quoteId }}</el-breadcrumb-item>
    </el-breadcrumb>

    <el-card shadow="never" class="summary">
      <div class="top-row">
        <el-button @click="goBack"><el-icon><Back /></el-icon>&nbsp;返回</el-button>
        <el-button v-if="canReview && data?.quote?.status === 'needs_review'" type="success"
                   @click="confirmReview"><el-icon><CircleCheck /></el-icon>&nbsp;核对此报价</el-button>
      </div>
      <div class="summary-main">
        <span class="name">{{ data?.material?.name || '—' }}</span>
        <span class="sep">·</span><span>{{ data?.material?.spec_model || '—' }}</span>
        <span class="sep">·</span><span>{{ data?.supplier?.name || '待确认' }}</span>
        <span class="sep">·</span><span class="quoter" v-if="data?.quoter">报价人 {{ fmtQuoter(data.quoter) }}</span>
        <span class="sep">·</span><span class="amount">¥{{ fmtAmount(data?.quote?.amount) }}</span>
        <span class="sep">·</span><span>{{ fmtDate(data?.quote?.quote_date) }}</span>
      </div>
      <div class="summary-tags">
        <el-tag :type="statusTag" size="small">{{ statusLabel }}</el-tag>
        <el-tag size="small" type="info">含税: {{ yn(data?.quote?.tax_included) }}</el-tag>
        <el-tag size="small" type="info">含运: {{ yn(data?.quote?.freight_included) }}</el-tag>
        <el-tag v-if="data?.quote?.channel" size="small">渠道: {{ data.quote.channel }}</el-tag>
      </div>
      <div class="ops">
        <el-button @click="goSameMaterial">查看同物料历史</el-button>
        <template v-if="isMaintainer">
          <el-dropdown @command="onMark">
            <el-button>标记异常<el-icon><ArrowDown /></el-icon></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="needs_review">待核对</el-dropdown-item>
                <el-dropdown-item command="no_valid_price">无有效报价</el-dropdown-item>
                <el-dropdown-item command="confirmed">已确认</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button type="primary" @click="$router.push(`/quotes/${quoteId}/edit`)">编辑</el-button>
          <el-button v-if="data?.quote?.status !== 'deleted'" type="danger" plain @click="onDelete">删除</el-button>
        </template>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-tabs>
        <el-tab-pane label="报价构成">
          <el-alert v-if="breakdownCount > 1" type="warning" :closable="false" class="bd-alert"
                    :title="`组合采购报价：识别到 ${breakdownCount} 家来源店，金额配对需人工核对补齐（Σ明细与总价对不上也算待核对）`" />
          <el-table :data="data?.breakdowns || []" size="small">
            <el-table-column prop="store_name" label="来源店铺" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <el-input v-if="isMaintainer && editing === row.id" v-model="rowEdit.store_name" size="small" />
                <span v-else>{{ row.store_name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="分项金额" width="140">
              <template #default="{ row }">
                <el-input-number v-if="isMaintainer && editing === row.id"
                                 v-model="rowEdit.amount" :min="0" :controls="false" :precision="2" size="small" />
                <span v-else>{{ fmtAmount(row.amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="说明" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">
                <el-input v-if="isMaintainer && editing === row.id" v-model="rowEdit.note" size="small" />
                <span v-else>{{ row.note || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'confirmed' ? 'success' : 'warning'" size="small">
                  {{ row.status === 'confirmed' ? '已确认' : '待核对' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column v-if="isMaintainer" label="" width="180">
              <template #default="{ row }">
                <template v-if="editing === row.id">
                  <el-button link type="primary" @click="saveRow(row)">保存</el-button>
                  <el-button link @click="editing = null">取消</el-button>
                </template>
                <template v-else>
                  <el-button link type="primary" @click="beginEdit(row)">编辑</el-button>
                  <el-button link type="danger" @click="deleteRow(row)">删除</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="isMaintainer" class="bd-add">
            <el-button size="small" @click="beginAdd"><el-icon><Plus /></el-icon> 添加明细</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="物料与需求">
          <el-descriptions :column="2" border v-if="data?.material">
            <el-descriptions-item label="物料编码">{{ data.material.code || '—' }}</el-descriptions-item>
            <el-descriptions-item label="物料名称">{{ data.material.name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="分类">{{ data.material.category || '—' }}</el-descriptions-item>
            <el-descriptions-item label="规格型号">{{ data.material.spec_model || '—' }}</el-descriptions-item>
            <el-descriptions-item label="技术参数" :span="2">{{ data.material.tech_params || '—' }}</el-descriptions-item>
            <el-descriptions-item label="零件号/图号">{{ data.material.part_no || '—' }}</el-descriptions-item>
            <el-descriptions-item label="材质">{{ data.material.material_text || '—' }}</el-descriptions-item>
            <el-descriptions-item label="品牌">{{ data.material.brand || '—' }}</el-descriptions-item>
            <el-descriptions-item label="进口/国产">{{ data.material.origin_type || '—' }}</el-descriptions-item>
            <el-descriptions-item label="单位">{{ data.material.unit || '—' }}</el-descriptions-item>
            <el-descriptions-item label="物料描述原文" :span="2">{{ data.material.name_raw || '—' }}</el-descriptions-item>
          </el-descriptions>
          <el-descriptions :column="2" border class="sub" v-if="data?.requirement">
            <el-descriptions-item label="需求数量">{{ data.requirement.quantity ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="使用单位">{{ data.requirement.unit || '—' }}</el-descriptions-item>
            <el-descriptions-item label="需求日期">
              {{ fmtDate(data.requirement.requirement_date) }}
              <el-tooltip v-if="data.requirement.requirement_date && data.quote?.date_inferred_from === 'template_date_row'"
                          content="该日期取自模板日期行（推断）"><el-tag size="small" type="warning">推断</el-tag></el-tooltip>
            </el-descriptions-item>
            <el-descriptions-item label="接收人">{{ data.requirement.receiver || '—' }}</el-descriptions-item>
            <el-descriptions-item label="报价行编号">{{ data.requirement.quote_row_no || '—' }}</el-descriptions-item>
            <el-descriptions-item label="需求备注">{{ data.requirement.remark || '—' }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="报价">
          <el-descriptions :column="2" border v-if="data?.quote">
            <el-descriptions-item label="金额(元)">{{ fmtAmount(data.quote.amount) }}</el-descriptions-item>
            <el-descriptions-item label="币种">{{ data.quote.currency }}</el-descriptions-item>
            <el-descriptions-item label="是否含税">{{ yn(data.quote.tax_included) }}</el-descriptions-item>
            <el-descriptions-item label="税率">{{ data.quote.tax_rate ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="是否含运">{{ yn(data.quote.freight_included) }}</el-descriptions-item>
            <el-descriptions-item label="可供数量">{{ data.quote.available_qty ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="交货日期">{{ fmtDate(data.quote.delivery_date) }}</el-descriptions-item>
            <el-descriptions-item label="运输方式">{{ data.quote.transport_mode || '—' }}</el-descriptions-item>
            <el-descriptions-item label="报价日期">{{ fmtDate(data.quote.quote_date) }}</el-descriptions-item>
            <el-descriptions-item label="有效期至">{{ fmtDate(data.quote.valid_until) }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ statusLabel }}</el-descriptions-item>
            <el-descriptions-item label="报价备注">{{ data.quote.remark || '—' }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="供应商">
          <el-descriptions :column="2" border v-if="data?.supplier">
            <el-descriptions-item label="供应商名称">{{ data.supplier.name }}
              <el-tag v-if="data.supplier.status === 'pending'" size="small" type="warning">待确认</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="来源渠道">{{ data.supplier.channel || '—' }}</el-descriptions-item>
            <el-descriptions-item label="联系人">{{ data.supplier.contact_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="电话">
              {{ data.supplier.phone || '—' }}
              <el-tag v-if="masked.includes('phone')" size="small" type="info">已按权限脱敏</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="地址">{{ data.supplier.address || '—' }}</el-descriptions-item>
            <el-descriptions-item label="银行账户">{{ data.supplier.bank_account || '—' }}</el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="供应商待确认" :image-size="60" />
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

        <el-tab-pane v-if="isMaintainer" label="修订记录">
          <el-table :data="revisions" size="small">
            <el-table-column prop="changed_at" label="时间" width="160">
              <template #default="{ row }">{{ fmtDateTime(row.changed_at) }}</template>
            </el-table-column>
            <el-table-column prop="changed_by_name" label="操作人" width="110" />
            <el-table-column prop="revision_type" label="类型" width="110" />
            <el-table-column prop="field" label="字段" width="130" />
            <el-table-column label="旧值 → 新值" min-width="220">
              <template #default="{ row }">
                <span class="old">{{ row.old_value ?? '—' }}</span> → <span class="new">{{ row.new_value ?? '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <div v-if="data?.sibling_quotes?.length" class="siblings">
        <div class="raw-title">兄弟报价（同一原始行拆分）</div>
        <el-tag v-for="s in data.sibling_quotes" :key="s.id" class="sib"
                @click="$router.push(`/quotes/${s.id}`)">
          #{{ s.id }} {{ s.group_label || '—' }} {{ fmtAmount(s.amount) }}
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Back, CircleCheck, Download, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { quoteDetail, quoteRevisions, deleteQuote, markStatus, fileDownloadUrl } from '../../api/quote'
import { addBreakdown, patchBreakdown, deleteBreakdown, patchQuote } from '../../api/maintenance'
import { useAuthStore } from '../../stores/auth'
import { fmtAmount, fmtDate, fmtDateTime, fmtQuoter, QUOTE_STATUS_MAP } from '../../utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const quoteId = computed(() => route.params.id as string)
const loading = ref(true)
const data = ref<any>(null)
const revisions = ref<any[]>([])

const isMaintainer = computed(() => auth.user && ['maintainer', 'admin'].includes(auth.user.role))
const statusLabel = computed(() => QUOTE_STATUS_MAP[data.value?.quote?.status]?.label || data.value?.quote?.status)
const statusTag = computed(() => QUOTE_STATUS_MAP[data.value?.quote?.status]?.tag || 'info')
const masked = computed(() => data.value?.masked_fields || [])
const canReview = computed(() => isMaintainer.value && data.value?.quote?.status !== 'deleted')
const breakdownCount = computed(() => (data.value?.breakdowns || []).length)
const yn = (v: boolean | null | undefined) => (v === true ? '是' : v === false ? '否' : '—')

const editing = ref<number | null>(null)
const rowEdit = reactive<any>({ store_name: '', amount: null, note: '' })

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/search')
}

async function confirmReview() {
  const { value } = await ElMessageBox.prompt(
    '请输入核对结论（将记入修订记录）：', '核对此报价', { inputValue: '对照原文件核实无误' })
  await markStatus(quoteId.value, 'confirmed', value)
  ElMessage.success('已核对确认')
  load()
}

function beginEdit(row: any) {
  editing.value = row.id
  rowEdit.store_name = row.store_name
  rowEdit.amount = row.amount
  rowEdit.note = row.note
}

async function beginAdd() {
  const { value } = await ElMessageBox.prompt('来源店铺名称', '添加报价构成明细', { inputValue: '' })
  const name = (value || '').trim()
  if (!name) return
  await addBreakdown(quoteId.value, { store_name: name, amount: null, note: null })
  ElMessage.success('已添加，请编辑金额后确认')
  load()
}

async function saveRow(row: any) {
  await patchBreakdown(quoteId.value, row.id, {
    store_name: rowEdit.store_name, amount: rowEdit.amount, note: rowEdit.note,
  })
  editing.value = null
  ElMessage.success('明细已更新并确认')
  load()
}

async function deleteRow(row: any) {
  await ElMessageBox.confirm(`删除明细「${row.store_name}」？`, '确认', { type: 'warning' })
  await deleteBreakdown(quoteId.value, row.id)
  ElMessage.success('已删除')
  load()
}

async function load() {
  loading.value = true
  try {
    data.value = await quoteDetail(quoteId.value)
    if (isMaintainer.value) {
      try { revisions.value = (await quoteRevisions(quoteId.value)).items } catch { revisions.value = [] }
    }
  } finally { loading.value = false }
}

function goSameMaterial() {
  const m = data.value?.material
  const kw = m?.code || m?.name || ''
  router.push({ path: '/search', query: { keyword: kw } })
}

async function onMark(status: string) {
  const { value } = await ElMessageBox.prompt('请输入标记原因', '标记异常', { inputValue: '' })
  await markStatus(quoteId.value, status, value)
  ElMessage.success('已标记')
  load()
}

async function onDelete() {
  await ElMessageBox.confirm('确认软删除该报价？删除后普通查询不可见，管理员可恢复。', '删除确认', { type: 'warning' })
  await deleteQuote(quoteId.value)
  ElMessage.success('已删除')
  router.push('/search')
}

function downloadFile() {
  window.open(fileDownloadUrl(data.value.source.file_id), '_blank')
}

watch(quoteId, load)
onMounted(load)
</script>

<style scoped>
.crumb { margin-bottom: 14px; }
.summary { margin-bottom: 14px; }
.summary :deep(.el-card__body) { padding: 18px 20px; }
.summary-main { font-size: 16px; display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
.summary-main .name { font-weight: 700; font-size: 20px; color: #0f172a; }
.summary-main .amount { color: #ef4444; font-weight: 700; font-size: 18px; font-variant-numeric: tabular-nums; }
.sep { color: #cbd5e1; }
.summary-tags { margin: 12px 0; display: flex; gap: 8px; flex-wrap: wrap; }
.ops { display: flex; gap: 8px; flex-wrap: wrap; }
.sub { margin-top: 12px; }
.raw-title { margin: 12px 0 6px; color: #64748b; font-size: 13px; }
.raw-cells {
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 12px; font-size: 12px; max-height: 260px; overflow: auto; white-space: pre-wrap;
}
.siblings { margin-top: 16px; }
.sib { margin-right: 8px; cursor: pointer; }
.old { color: #94a3b8; }
.new { color: #16a34a; font-weight: 500; }
</style>
