<template>
  <div>
    <el-breadcrumb class="crumb">
      <el-breadcrumb-item>报价搜索</el-breadcrumb-item>
    </el-breadcrumb>
    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <el-input v-model="filters.keyword" placeholder="物料名称 / 编码 / 型号 / 品牌 / 供应商 / 备注" clearable
                  style="width: 420px" @keyup.enter="doSearch" @clear="doSearch" />
        <el-button type="primary" @click="doSearch">搜索</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
      <div class="filter-row">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
                        start-placeholder="报价日期起" end-placeholder="报价日期止" style="width: 260px" @change="doSearch" />
        <el-select v-model="filters.supplier_id" placeholder="供应商" clearable filterable remote
                   :remote-method="loadSuppliers" :loading="supplierLoading" style="width: 180px" @change="doSearch">
          <el-option v-for="s in supplierOptionsList" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-select v-model="filters.unit" placeholder="使用单位" clearable filterable style="width: 150px" @change="doSearch">
          <el-option v-for="u in units" :key="u" :label="u" :value="u" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 130px" @change="doSearch">
          <el-option v-for="(cfg, key) in statusMap" :key="key" :label="cfg.label" :value="key" />
        </el-select>
        <el-input-number v-model="filters.price_min" :min="0" :controls="false" placeholder="价格≥" style="width: 100px" @change="doSearch" />
        <span class="dash">~</span>
        <el-input-number v-model="filters.price_max" :min="0" :controls="false" placeholder="≤" style="width: 100px" @change="doSearch" />
        <el-select v-model="filters.tax_included" placeholder="含税" clearable style="width: 100px" @change="doSearch">
          <el-option label="含税" :value="true" /><el-option label="不含税" :value="false" />
        </el-select>
        <el-select v-model="filters.freight_included" placeholder="含运" clearable style="width: 100px" @change="doSearch">
          <el-option label="含运" :value="true" /><el-option label="不含运" :value="false" />
        </el-select>
        <el-checkbox v-model="includeRequirement" @change="doSearch">含无报价需求</el-checkbox>
      </div>
      <div v-if="appliedChips.length" class="chips">
        <el-tag v-for="c in appliedChips" :key="c.key" closable size="small" @close="removeChip(c.key)">
          {{ c.label }}
        </el-tag>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="rows" stripe @row-click="goDetail" style="cursor: pointer">
        <el-table-column prop="material_name" label="物料名称" min-width="130" show-overflow-tooltip />
        <el-table-column prop="material_code" label="物料编码" width="110" />
        <el-table-column prop="spec_model" label="规格型号" min-width="150" show-overflow-tooltip />
        <el-table-column prop="brand" label="品牌" width="90" />
        <el-table-column prop="supplier_name" label="供应商" min-width="130" show-overflow-tooltip />
        <el-table-column label="报价人" width="80">
          <template #default="{ row }">{{ fmtQuoter(row.quoter) }}</template>
        </el-table-column>
        <el-table-column label="金额(元)" width="110" align="right">
          <template #default="{ row }"><span class="amount-cell">{{ fmtAmount(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column label="含税/含运" width="90">
          <template #default="{ row }">
            <span v-if="row.row_type === 'requirement'">— / —</span>
            <span v-else>{{ yn(row.tax_included) }} / {{ yn(row.freight_included) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quote_date" label="报价日期" width="110" sortable />
        <el-table-column prop="source_summary" label="来源" min-width="180" show-overflow-tooltip />
        <el-table-column label="" width="70">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="goDetail(row)">详情</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="empty-state">
            <p>未找到匹配记录</p>
            <p v-if="appliedChips.length" class="applied">
              当前筛选：{{ appliedChips.map(c => c.label).join('；') }}
            </p>
            <el-button v-if="appliedChips.length" @click="resetFilters">清除全部筛选</el-button>
          </div>
        </template>
      </el-table>
      <div class="pager">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
                       :total="total" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next"
                       @current-change="load" @size-change="load" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { searchQuotes, supplierOptions, unitOptions } from '../../api/quote'
import { fmtAmount, fmtQuoter, QUOTE_STATUS_MAP } from '../../utils/format'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dateRange = ref<[string, string] | null>(null)
const units = ref<string[]>([])
const supplierOptionsList = ref<any[]>([])
const supplierLoading = ref(false)
const statusMap = QUOTE_STATUS_MAP
const includeRequirement = ref(false)

const filters = reactive<any>({
  keyword: (route.query.keyword as string) || '',
  supplier_id: undefined, unit: undefined, status: undefined,
  price_min: undefined, price_max: undefined,
  tax_included: undefined, freight_included: undefined,
})

const appliedChips = computed(() => {
  const chips: { key: string; label: string }[] = []
  if (filters.keyword) chips.push({ key: 'keyword', label: `关键词="${filters.keyword}"` })
  if (dateRange.value) chips.push({ key: 'date', label: `日期=${dateRange.value[0]}~${dateRange.value[1]}` })
  if (filters.supplier_id) chips.push({ key: 'supplier_id', label: '供应商已选' })
  if (filters.unit) chips.push({ key: 'unit', label: `使用单位=${filters.unit}` })
  if (filters.status) chips.push({ key: 'status', label: `状态=${statusMap[filters.status]?.label}` })
  if (filters.price_min != null || filters.price_max != null)
    chips.push({ key: 'price', label: `价格=${filters.price_min ?? 0}~${filters.price_max ?? '∞'}` })
  if (filters.tax_included !== undefined && filters.tax_included !== null)
    chips.push({ key: 'tax', label: filters.tax_included ? '含税' : '不含税' })
  if (filters.freight_included !== undefined && filters.freight_included !== null)
    chips.push({ key: 'freight', label: filters.freight_included ? '含运' : '不含运' })
  return chips
})

const statusLabel = (s: string) => statusMap[s]?.label || (s === 'no_quote' ? '无报价' : s)
const statusTag = (s: string) => (s === 'no_quote' ? 'warning' : statusMap[s]?.tag || 'info')
const yn = (v: boolean | null) => (v === true ? '是' : v === false ? '否' : '—')

async function loadSuppliers(kw?: string) {
  supplierLoading.value = true
  try {
    const data = await supplierOptions(kw)
    supplierOptionsList.value = data.items
  } finally { supplierLoading.value = false }
}

async function doSearch() {
  page.value = 1
  // 同步 URL query（可分享/刷新保留）
  router.replace({ query: { ...route.query, keyword: filters.keyword || undefined } })
  await load()
}

function removeChip(key: string) {
  if (key === 'keyword') filters.keyword = ''
  if (key === 'date') dateRange.value = null
  if (key === 'supplier_id') filters.supplier_id = undefined
  if (key === 'unit') filters.unit = undefined
  if (key === 'status') filters.status = undefined
  if (key === 'price') { filters.price_min = undefined; filters.price_max = undefined }
  if (key === 'tax') filters.tax_included = undefined
  if (key === 'freight') filters.freight_included = undefined
  doSearch()
}

function resetFilters() {
  Object.assign(filters, { keyword: '', supplier_id: undefined, unit: undefined, status: undefined,
    price_min: undefined, price_max: undefined, tax_included: undefined, freight_included: undefined })
  dateRange.value = null
  doSearch()
}

async function load() {
  loading.value = true
  try {
    const data = await searchQuotes({
      ...filters,
      date_from: dateRange.value?.[0], date_to: dateRange.value?.[1],
      page: page.value, pageSize: pageSize.value,
      include_requirement: includeRequirement.value,
    })
    rows.value = includeRequirement.value
      ? [...data.items, ...(data.requirement_items || [])]
      : data.items
    total.value = data.total
  } finally { loading.value = false }
}

function goDetail(row: any) {
  if (row.row_type === 'requirement') {
    router.push(`/requirements/${row.requirement_id}`)
  } else {
    router.push(`/quotes/${row.id}`)
  }
}

onMounted(async () => {
  loadSuppliers()
  try { units.value = (await unitOptions()).items } catch { units.value = [] }
  await load()
})
</script>

<style scoped>
.crumb { margin-bottom: 14px; }
.filter-card { margin-bottom: 14px; }
.filter-card :deep(.el-card__body) { padding: 14px 16px 6px; }
.filter-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.filter-row:last-child { margin-bottom: 0; }
.dash { color: #94a3b8; }
.chips { margin-top: 10px; padding-top: 10px; border-top: 1px dashed #e2e8f0; display: flex; gap: 6px; flex-wrap: wrap; }
.pager { margin-top: 14px; display: flex; justify-content: flex-end; }
.empty-state { padding: 28px 0; }
.applied { color: #94a3b8; font-size: 13px; }
.amount-cell { font-variant-numeric: tabular-nums; font-weight: 600; color: #0f172a; }
.src-cell { color: #64748b; font-size: 12px; }
</style>
