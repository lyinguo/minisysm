<template>
  <section class="warehouse-document-report">
    <div class="toolbar">
      <el-input
        v-model="number"
        placeholder="单据编号"
        clearable
        @keyup.enter="search"
        style="width: 240px"
      />
      <el-button type="primary" @click="search">查询</el-button>
      <el-button @click="loadList">刷新</el-button>
      <el-button @click="exportPage">导出当前页</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" border row-key="id">
      <el-table-column prop="frameName" label="所属组织" min-width="120" />
      <el-table-column prop="number" label="单据编号" min-width="180" />
      <el-table-column label="单据时间" min-width="170"
        ><template #default="{ row }">{{ formatTime(row.time) }}</template></el-table-column
      >
      <el-table-column prop="total" label="单据成本" min-width="120" />
      <el-table-column prop="cost" label="单据费用" min-width="120" />
      <el-table-column label="审核状态" width="100"
        ><template #default="{ row }">{{
          Number(row.examine) === 1 ? '已审核' : '未审核'
        }}</template></el-table-column
      >
      <el-table-column prop="data" label="备注" min-width="160" />
      <el-table-column label="操作" width="170" fixed="right"
        ><template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row.id)">详情 / 编辑</el-button>
          <el-button link @click="printRow(row)">打印</el-button>
        </template></el-table-column
      >
    </el-table>
    <el-pagination
      v-model:current-page="page"
      :page-size="size"
      :total="total"
      layout="total,prev,pager,next"
      @current-change="loadList"
    />
    <el-dialog
      v-model="visible"
      :title="title + '详情'"
      width="92%"
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div v-loading="detailLoading">
        <template v-if="draft">
          <el-alert
            v-if="!draft.items.length"
            title="该单据缺少商品明细，不能保存或审核。请先在单据管理中补全数据。"
            type="warning"
            :closable="false"
          />
          <el-alert
            v-if="checked"
            title="单据已核对，修改前请在入库开单页反核对；可以直接审核当前版本。"
            type="info"
            :closable="false"
          />
          <el-form label-width="90px" :disabled="editingLocked">
            <el-form-item label="单据编号"><el-input v-model="draft.header.number" /></el-form-item>
            <el-form-item label="单据时间"
              ><el-date-picker
                v-model="draft.header.time"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm:ss"
            /></el-form-item>
            <el-form-item label="备注"><el-input v-model="draft.header.data" /></el-form-item>
          </el-form>
          <el-table :data="draft.items" border>
            <el-table-column label="商品" min-width="160"
              ><template #default="{ row }">{{ productName(row.goods) }}</template></el-table-column
            >
            <el-table-column prop="attr" label="辅助属性" width="100" />
            <el-table-column prop="unit" label="单位" width="80" />
            <el-table-column :label="kind === 'swap' ? '调出仓库' : '仓库'" min-width="160"
              ><template #default="{ row }">
                <el-select-v2
                  v-model="row.warehouse"
                  :disabled="editingLocked"
                  filterable
                  :options="warehouseOptions"
                /> </template
            ></el-table-column>
            <el-table-column v-if="kind === 'swap'" label="调入仓库" min-width="160"
              ><template #default="{ row }">
                <el-select-v2
                  v-model="row.storehouse"
                  :disabled="editingLocked"
                  filterable
                  :options="warehouseOptions"
                /> </template
            ></el-table-column>
            <el-table-column label="数量" min-width="160"
              ><template #default="{ row }"
                ><el-input-number
                  v-model="row.nums"
                  :precision="4"
                  :min="0.0001"
                  :disabled="editingLocked" /></template
            ></el-table-column>
            <el-table-column label="单位成本" min-width="160"
              ><template #default="{ row }"
                ><el-input-number
                  v-model="row.price"
                  :precision="4"
                  :min="0"
                  :disabled="editingLocked" /></template
            ></el-table-column>
            <el-table-column label="总成本" width="120"
              ><template #default="{ row }">{{
                (Number(row.nums) * Number(row.price)).toFixed(4)
              }}</template></el-table-column
            >
            <el-table-column prop="batch" label="批次号" width="130" />
            <el-table-column prop="mfd" label="生产日期" width="120" />
            <el-table-column
              v-if="draft.goods.some((g) => Number(g.serial) === 1)"
              label="序列号JSON数组"
              min-width="180"
              ><template #default="{ row }"
                ><el-input
                  v-model="row.serial"
                  type="textarea"
                  :disabled="editingLocked"
                  placeholder='["SN001"]' /></template
            ></el-table-column>
            <el-table-column label="备注" min-width="160"
              ><template #default="{ row }"
                ><el-input v-model="row.data" :disabled="editingLocked" /></template
            ></el-table-column>
          </el-table>
          <p>单据费用和商品资料保持原值；审核前可修改现有明细的仓库、数量、成本及备注。</p>
        </template>
      </div>
      <template #footer>
        <el-button :disabled="busy" @click="visible = false">关闭</el-button>
        <el-button v-if="draft && !audited && !checked" type="primary" :loading="busy" @click="save"
          >保存</el-button
        >
        <el-button v-if="draft && !audited" type="success" :loading="busy" @click="audit(1)"
          >保存并审核</el-button
        >
        <el-button v-if="draft && audited" type="warning" :loading="busy" @click="audit(0)"
          >反审核</el-button
        >
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useHttp } from '@/plugins/http'
import { CommonAPI } from '@/apis/common/api'
import { printDocument } from '@/utils/printDocument'

const props = defineProps<{ kind: 'entry' | 'extry' | 'swap'; title: string }>()
type Row = Record<string, any>
type Detail = { version: string; header: Row; items: Row[]; goods: Row[] }
const base = `/transfer/report-documents/${props.kind}`
const http = useHttp()
const rows = ref<Row[]>([])
const loading = ref(false)
const page = ref(1)
const size = 20
const total = ref(0)
const number = ref('')
const warehouses = ref<Array<{ id: string; name: string }>>([])
const warehouseOptions = computed(() =>
  warehouses.value.map((w) => ({ value: String(w.id), label: w.name }))
)
const draft = ref<Detail | null>(null)
const visible = ref(false)
const busy = ref(false)
const detailLoading = ref(false)
const audited = computed(() => Number(draft.value?.header.examine) === 1)
const checked = computed(() => props.kind === 'entry' && Number(draft.value?.header.check) === 1)
const editingLocked = computed(() => audited.value || checked.value || busy.value)
let original = ''
function content() {
  return JSON.stringify([draft.value?.header, draft.value?.items])
}
let active = true
let requestId = 0
let detailRequestId = 0
onBeforeUnmount(() => {
  active = false
  requestId++
  detailRequestId++
})

function formatTime(value: unknown) {
  if (typeof value === 'number') {
    const date = new Date(value)
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
  }
  return String(value ?? '')
    .replace('T', ' ')
    .slice(0, 19)
}
function unwrap<T>(response: { code: number; data?: T; message?: string }): T {
  if (response.code !== 10000 || response.data == null)
    throw new Error(response.message || '请求失败')
  return response.data
}
function fail(error: unknown) {
  if (active) ElMessage.error(error instanceof Error ? error.message : '操作失败')
}
async function loadList() {
  const seq = ++requestId
  loading.value = true
  try {
    const data = unwrap(
      await http.get<{ rows: Row[]; total: number }>(base, {
        pageIndex: page.value,
        pageSize: size,
        number: number.value
      })
    )
    if (active && seq === requestId) {
      rows.value = Array.isArray(data.rows) ? data.rows : []
      total.value = Number(data.total) || 0
    }
  } catch (error) {
    if (seq === requestId) fail(error)
  } finally {
    if (active && seq === requestId) loading.value = false
  }
}
function search() {
  page.value = 1
  return loadList()
}
function applyDetail(data: Detail) {
  data.header.time = formatTime(data.header.time)
  data.items.forEach((item) => {
    item.nums = Number(item.nums)
    item.price = Number(item.price)
    item.warehouse = String(item.warehouse ?? '')
    if (item.storehouse != null) item.storehouse = String(item.storehouse)
  })
  draft.value = data
  original = content()
}
async function openDetail(id: string) {
  const seq = ++detailRequestId
  draft.value = null
  visible.value = true
  detailLoading.value = true
  try {
    const data = unwrap(await http.get<Detail>(`${base}/${encodeURIComponent(id)}`))
    if (active && seq === detailRequestId) applyDetail(data)
  } catch (error) {
    fail(error)
  } finally {
    if (active && seq === detailRequestId) detailLoading.value = false
  }
}
function productName(id: string) {
  return draft.value?.goods?.find((g) => String(g.id) === String(id))?.name || id
}
async function persist() {
  if (!draft.value) throw new Error('请重新打开单据详情')
  const id = encodeURIComponent(String(draft.value.header.id))
  const data = unwrap(await http.put<Detail>(`${base}/${id}`, draft.value))
  if (active) applyDetail(data)
}
async function save() {
  if (busy.value) return
  busy.value = true
  try {
    await persist()
    if (active) ElMessage.success('保存成功')
    await loadList()
  } catch (error) {
    fail(error)
  } finally {
    busy.value = false
  }
}
async function audit(target: 0 | 1) {
  if (!draft.value || busy.value) return
  busy.value = true
  try {
    await ElMessageBox.confirm(
      target === 1
        ? '审核会更新真实库存，是否继续？'
        : '反审核会还原库存，库存不足时不能反审核。是否继续？',
      '确认操作',
      { type: 'warning' }
    )
    if (target === 1 && content() !== original) await persist()
    const id = encodeURIComponent(String(draft.value!.header.id))
    const data = unwrap(
      await http.post<Detail>(`${base}/${id}/audit`, { target, version: draft.value!.version })
    )
    if (active) {
      applyDetail(data)
      ElMessage.success(target === 1 ? '审核成功，库存已更新' : '反审核成功，库存已还原')
    }
    await loadList()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') fail(error)
  } finally {
    busy.value = false
  }
}
const printColumns = [
  { prop: 'number', label: '单据编号' },
  { prop: 'time', label: '单据时间' },
  { prop: 'total', label: '单据成本' },
  { prop: 'cost', label: '单据费用' },
  { prop: 'data', label: '备注' }
]
function printRow(row: Row) {
  printDocument(props.title, printColumns, [{ ...row, time: formatTime(row.time) }])
}
async function exportPage() {
  try {
    const { utils, writeFile } = await import('xlsx')
    const book = utils.book_new()
    const data = rows.value.map((row) =>
      Object.fromEntries(
        printColumns.map((column) => [
          column.label,
          column.prop === 'time' ? formatTime(row.time) : row[column.prop]
        ])
      )
    )
    utils.book_append_sheet(book, utils.json_to_sheet(data), '单据')
    writeFile(book, `${props.title}.xlsx`)
  } catch (error) {
    fail(error)
  }
}
onMounted(() => {
  void loadList()
  void CommonAPI.getWarehouseNameList()
    .then((data) => {
      if (active) warehouses.value = data
    })
    .catch(fail)
})
</script>

<style scoped>
.warehouse-document-report {
  padding: 16px;
  height: 100%;
  overflow: auto;
  box-sizing: border-box;
}
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.el-pagination {
  margin-top: 16px;
}
</style>
