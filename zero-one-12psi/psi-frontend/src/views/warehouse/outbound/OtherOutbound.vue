<template>
  <section class="inbound-workspace">
    <header>
      <div>
        <h2>其他出库</h2>
        <p>用于盘亏、损耗、赠出等非销售出库。销售发货请走销售单，避免遗漏客户应收。</p>
      </div>
      <el-tag>{{
        id ? (audited ? '已审核 · 已出库' : checked ? '已核对' : '草稿 · 未出库') : '新单据'
      }}</el-tag>
    </header>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <div class="actions">
      <el-button :disabled="busy" @click="newDocument">新建</el-button>
      <el-button type="primary" :disabled="locked" @click="save">保存草稿</el-button>
      <el-button :disabled="!id || audited || busy || dirty" @click="changeCheck">{{
        checked ? '反核对' : '核对'
      }}</el-button>
      <el-button type="success" :disabled="busy || (!id && !items.length)" @click="changeAudit">{{
        audited ? '反审核' : '审核出库'
      }}</el-button>
      <el-button type="danger" plain :disabled="!id || checked || audited || busy" @click="remove"
        >删除草稿</el-button
      >
      <el-button @click="router.push({ name: 'WarehouseOtherOutboundReport' })">出库报表</el-button>
      <el-button :disabled="!id || busy" @click="exportFile(false)">导出此单汇总</el-button>
      <el-button :disabled="!id || busy" @click="exportFile(true)">导出此单明细</el-button>
    </div>
    <el-alert
      title="保存只生成草稿；审核才扣减库存。修改已核对的单据，须先反审核、再反核对。"
      type="info"
      :closable="false"
    />
    <div class="workspace-grid">
      <main>
        <el-form label-position="top" :disabled="locked" class="header-form">
          <el-form-item label="关联客户（选填，仅用于追溯）">
            <el-select-v2
              v-model="header.customer"
              aria-label="关联客户"
              clearable
              filterable
              :options="customers.map((c) => ({ value: String(c.id), label: c.name }))"
            />
          </el-form-item>
          <el-form-item label="出库单号"
            ><el-input v-model="header.number" aria-label="出库单号" maxlength="32"
          /></el-form-item>
          <el-form-item label="单据日期"
            ><el-date-picker
              v-model="header.time"
              aria-label="单据日期"
              type="datetime"
              value-format="YYYY-MM-DD HH:mm:ss"
          /></el-form-item>
          <el-form-item label="单据类型"
            ><el-select v-model="header.type"
              ><el-option :value="0" label="其他出库" /><el-option
                :value="1"
                label="盘亏" /></el-select
          ></el-form-item>
        </el-form>
        <p v-if="frameName">所属组织：{{ frameName }}</p>
        <el-button :disabled="locked" @click="picker = true">选择商品</el-button>
        <el-table
          :data="items"
          border
          empty-text="点击“选择商品”添加明细，再选择出库仓库、填写数量和成本。"
        >
          <el-table-column label="商品" min-width="170"
            ><template #default="{ row }"
              >{{ row.name }}<small>{{ row.number }}</small></template
            ></el-table-column
          >
          <el-table-column label="基本单位" width="90"
            ><template #default="{ row }">{{ unitName(row.unit) }}</template></el-table-column
          >
          <el-table-column label="出库仓库" min-width="170"
            ><template #default="{ row }"
              ><el-select-v2
                v-model="row.warehouse"
                aria-label="出库仓库"
                filterable
                :options="warehouseOptions"
                :disabled="locked"
                placeholder="请选择出库仓库" /></template
          ></el-table-column>
          <el-table-column label="数量" min-width="165"
            ><template #default="{ row }"
              ><el-input-number
                v-model="row.nums"
                aria-label="出库数量"
                :disabled="locked"
                :min="0.0001"
                :max="99999999"
                :precision="4" /></template
          ></el-table-column>
          <el-table-column label="单位成本" min-width="165"
            ><template #default="{ row }"
              ><span v-if="audited">{{
                row.actualPrice == null ? '待核对' : Number(row.actualPrice).toFixed(4)
              }}</span
              ><el-input-number
                v-else
                v-model="row.price"
                aria-label="单位成本"
                :disabled="locked"
                :min="0"
                :max="99999999"
                :precision="4" /></template
          ></el-table-column>
          <el-table-column label="成本金额" width="110"
            ><template #default="{ row }">{{
              audited
                ? row.actualCost == null
                  ? '待核对'
                  : Number(row.actualCost).toFixed(4)
                : amount(row).toFixed(4)
            }}</template></el-table-column
          >
          <el-table-column
            v-if="items.some((i) => i.batchEnabled)"
            label="批次 / 生产日期"
            min-width="200"
            ><template #default="{ row }"
              ><template v-if="row.batchEnabled"
                ><el-input
                  v-model="row.batch"
                  :disabled="locked"
                  placeholder="批次号" /><el-date-picker
                  v-model="row.mfd"
                  type="date"
                  value-format="YYYY-MM-DD"
                  :disabled="locked" /></template></template
          ></el-table-column>
          <el-table-column
            v-if="items.some((i) => i.serialEnabled)"
            label="序列号（每行一个）"
            min-width="160"
            ><template #default="{ row }"
              ><el-input
                v-if="row.serialEnabled"
                v-model="row.serialText"
                type="textarea"
                :disabled="locked" /></template
          ></el-table-column>
          <el-table-column width="80"
            ><template #default="{ $index }"
              ><el-button link type="danger" :disabled="locked" @click="items.splice($index, 1)"
                >移除</el-button
              ></template
            ></el-table-column
          >
        </el-table>
        <p class="total">
          {{ items.length }} 行商品，{{ audited ? '实际成本' : '预计成本' }}
          {{
            audited
              ? header.actualCost == null
                ? '待核对'
                : Number(header.actualCost).toFixed(4)
              : total.toFixed(4)
          }}
          元
        </p>
        <el-input
          v-model="header.data"
          aria-label="出库备注"
          type="textarea"
          :disabled="locked"
          placeholder="填写出库原因，便于追溯"
        />
        <p v-if="costs.length">
          保留原单 {{ costs.length }} 项费用及附件、物流资料。本页不修改费用结算。
        </p>
      </main>
      <aside>
        <h3>已保存单据</h3>
        <el-input
          v-model="keyword"
          placeholder="按出库单号查询"
          aria-label="查询出库单号"
          @keyup.enter="loadList"
        />
        <el-button :loading="listLoading" @click="loadList">查询 / 刷新</el-button>
        <el-empty v-if="!documents.length" description="暂无匹配单据" :image-size="50" />
        <button
          v-for="document in documents"
          :key="document.id"
          class="document"
          :class="{ selected: document.id === id }"
          :disabled="busy"
          @click="open(document.id)"
        >
          <strong>{{ document.number }}</strong
          ><span
            >{{
              Number(document.examine) === 1
                ? '已审核'
                : Number(document.check) === 1
                  ? '已核对'
                  : '草稿'
            }}
            ·
            {{
              Number(document.examine) === 1 ? (document.actualCost ?? '待核对') : document.total
            }}
            元</span
          ><span>{{ document.frameName }}</span>
        </button>
        <el-pagination
          v-model:current-page="page"
          :page-size="20"
          :total="count"
          layout="prev,pager,next"
          @current-change="loadList"
        />
      </aside>
    </div>
    <OperationPopTable v-if="picker" @confirm="choose" @close="picker = false" />
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useHttp } from '@/plugins/http'
import OperationPopTable from '@/components/operationpoptable/OperationPopTable.vue'
import { downloadExportBlob } from '@/utils/reportMappers'
type Row = Record<string, any>
const http = useHttp(),
  router = useRouter(),
  route = useRoute()
const header = reactive<Row>({}),
  items = ref<Row[]>([]),
  costs = ref<Row[]>([]),
  warehouses = ref<Row[]>([]),
  customers = ref<Row[]>([]),
  units = ref<Row[]>([]),
  documents = ref<Row[]>([])
const id = ref(''),
  version = ref(''),
  frameName = ref(''),
  error = ref(''),
  keyword = ref(''),
  busy = ref(false),
  listLoading = ref(false),
  picker = ref(false),
  page = ref(1),
  count = ref(0)
let original = ''
const signature = () => JSON.stringify([header, items.value, costs.value])
const dirty = computed(() => signature() !== original),
  audited = computed(() => Number(header.examine) === 1),
  checked = computed(() => Number(header.check) === 1)
const locked = computed(
  () => busy.value || audited.value || checked.value || [1, 2].includes(Number(header.cse))
)
const warehouseOptions = computed(() =>
  warehouses.value.map((w) => ({
    value: String(w.id),
    label: `${w.name}${w.number ? ' · ' + w.number : ''}`
  }))
)
const amount = (row: Row) => Number((Number(row.nums || 0) * Number(row.price || 0)).toFixed(4))
const total = computed(() =>
  Number(items.value.reduce((sum, row) => sum + amount(row), 0).toFixed(4))
)
const unitName = (value: string) => units.value.find((u) => String(u.id) === value)?.name || value
function unwrap(response: any) {
  if (response.code !== 10000 || response.data == null)
    throw Error(response.message || '操作未成功')
  return response.data
}
function fail(e: unknown) {
  error.value =
    e instanceof Error ? e.message : typeof e === 'string' ? e : '操作失败，请刷新后重试'
}
function time(value: any) {
  const date = new Date(typeof value === 'number' ? value : String(value).replace(' ', 'T'))
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}
function reset() {
  Object.keys(header).forEach((k) => delete header[k])
  Object.assign(header, {
    customer: '',
    people: '',
    number: 'QTCK' + Date.now() + Math.random().toString(16).slice(2, 6),
    time: time(Date.now()),
    type: 0,
    data: '',
    examine: 0,
    check: 0,
    cse: 3
  })
  id.value = ''
  version.value = ''
  items.value = []
  costs.value = []
  frameName.value = ''
  original = signature()
  error.value = ''
}
async function options() {
  const data = unwrap(await http.get('/otherout/options', id.value ? { id: id.value } : {}))
  warehouses.value = Array.isArray(data.warehouses) ? data.warehouses : []
  customers.value = Array.isArray(data.customers) ? data.customers : []
  units.value = data.units || []
}
async function loadList() {
  listLoading.value = true
  try {
    const data = unwrap(
      await http.get('/otherout/list', {
        number: keyword.value,
        pageIndex: page.value,
        pageSize: 20
      })
    )
    documents.value = Array.isArray(data.rows) ? data.rows : []
    count.value = Number(data.total) || 0
  } catch (e) {
    fail(e)
  } finally {
    listLoading.value = false
  }
}
async function discard() {
  if (dirty.value)
    await ElMessageBox.confirm('当前修改尚未保存，是否放弃？', '切换单据', { type: 'warning' })
}
async function newDocument() {
  try {
    await discard()
    reset()
    await router.replace({ query: {} })
    await options()
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') fail(e)
  }
}
function baseUnit(product: Row) {
  if (String(product.unit) !== '-1') return String(product.unit || '')
  try {
    return String(JSON.parse(product.units || '[]')[0]?.source || '')
  } catch {
    return ''
  }
}
function choose(products: Row[]) {
  for (const p of products)
    items.value.push({
      goods: String(p.id),
      name: p.name,
      number: p.number || p.code,
      attr: p.selectedAttr || '',
      unit: baseUnit(p),
      warehouse: '',
      price: Number(p.purchasePrice ?? p.buy ?? 0),
      nums: Number(p.quantity || 1),
      batch: '',
      mfd: null,
      batchEnabled: Number(p.batch) === 1,
      serialEnabled: Number(p.serial) === 1,
      serialText: '',
      data: ''
    })
  picker.value = false
}
async function reload() {
  const data = unwrap(await http.get('/otherout/getInfo', { id: id.value }))
  Object.keys(header).forEach((k) => delete header[k])
  Object.assign(header, data.header, { time: time(data.header.time) })
  version.value = data.version
  costs.value = data.costs || []
  frameName.value = data.frameName
  warehouses.value = data.warehouses || []
  units.value = data.units || []
  items.value = data.items.map((item: Row) => {
    const product = data.goods.find((p: Row) => String(p.id) === String(item.goods)) || {}
    return {
      ...item,
      nums: Number(item.nums),
      price: Number(item.price),
      name: product.name || item.goods,
      number: product.number,
      batchEnabled: Number(product.batch) === 1,
      serialEnabled: Number(product.serial) === 1,
      serialText: JSON.parse(item.serial || '[]').join('\n')
    }
  })
  original = signature()
  try {
    await options()
  } catch (e) {
    fail(e)
  }
}
async function open(identifier: string) {
  try {
    await discard()
    busy.value = true
    error.value = ''
    id.value = identifier
    await reload()
    await router.replace({ query: { id: identifier } })
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') fail(e)
  } finally {
    busy.value = false
  }
}
function metadata(value: any) {
  if (value == null) return null
  return typeof value === 'string' ? value : JSON.stringify(value)
}
function payload() {
  if (!header.number?.trim() || !header.time) throw Error('请填写出库单号和日期')
  if (!items.value.length) throw Error('请先选择商品')
  const lines = items.value.map((row) => {
    if (!row.warehouse || !row.unit) throw Error('请为每行商品选择仓库，并确认基本单位')
    if (!Number.isFinite(row.nums) || row.nums <= 0 || !Number.isFinite(row.price) || row.price < 0)
      throw Error('数量必须大于零，单位成本不能为负数')
    if (row.batchEnabled && (!row.batch || !row.mfd)) throw Error('批次商品需要批次号和生产日期')
    const serial = String(row.serialText || '')
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean)
    if (row.serialEnabled && serial.length !== Number(row.nums))
      throw Error('每件序列号商品需填写一个序列号')
    return {
      ...row,
      goods: String(row.goods),
      serial: JSON.stringify(serial),
      mfd: row.mfd ? String(row.mfd).slice(0, 10) + 'T00:00:00' : null,
      total: amount(row)
    }
  })
  return {
    ...header,
    time: String(header.time).replace(' ', 'T'),
    customer: header.customer || '',
    people: header.people || '',
    file: metadata(header.file),
    more: metadata(header.more),
    logistics: metadata(header.logistics),
    total: total.value,
    examine: 0,
    check: 0,
    cost: Number(header.cost || 0),
    cse: costs.value.length ? 0 : 3,
    costDTOList: costs.value,
    otherOutListInfoDTOList: lines
  }
}
async function persist() {
  const body = payload()
  if (id.value)
    unwrap(await http.put('/otherout/update', { ...body, id: id.value, version: version.value }))
  else id.value = String(unwrap(await http.post('/otherout/add', body)))
  await reload()
  await router.replace({ query: { id: id.value } })
}
async function save() {
  if (locked.value) return
  busy.value = true
  error.value = ''
  try {
    await persist()
    ElMessage.success('草稿已保存，尚未出库')
    await loadList()
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}
const command = (target?: number) => ({
  ids: [id.value],
  versions: { [id.value]: version.value },
  ...(target == null ? {} : { target })
})
async function changeCheck() {
  if (!id.value || dirty.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    unwrap(await http.put('/otherout/check', command(checked.value ? 0 : 1)))
    await reload()
    await loadList()
    ElMessage.success(checked.value ? '已核对' : '已反核对')
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}
async function changeAudit() {
  if (busy.value) return
  try {
    const target = audited.value ? 0 : 1
    await ElMessageBox.confirm(
      target
        ? '审核将扣减真实库存；库存或所选批次、序列号不足时整单拒绝。是否继续？'
        : '反审核将撤回原出库，存在后续关联或已结账时会拒绝。是否继续？',
      '库存操作',
      { type: 'warning' }
    )
    busy.value = true
    error.value = ''
    if (target && (!id.value || dirty.value)) await persist()
    unwrap(await http.put('/otherout/examine', command(target)))
    await reload()
    await loadList()
    ElMessage.success(target ? '审核成功，库存已扣减' : '反审核成功，原出库已撤回')
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') fail(e)
  } finally {
    busy.value = false
  }
}
async function remove() {
  try {
    await ElMessageBox.confirm(
      '删除将永久移除此草稿和明细，操作记录仍保留。是否继续？',
      '删除草稿',
      { type: 'warning' }
    )
    busy.value = true
    unwrap(await http.delete('/otherout/delete', command()))
    reset()
    await router.replace({ query: {} })
    await loadList()
    ElMessage.success('草稿已删除')
    try {
      await options()
    } catch (e) {
      fail(e)
    }
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') fail(e)
  } finally {
    busy.value = false
  }
}
onMounted(async () => {
  reset()
  if (route.query.id) await open(String(route.query.id))
  else
    try {
      await options()
    } catch (e) {
      fail(e)
    }
  await loadList()
})
async function exportFile(detail: boolean) {
  if (!id.value || busy.value) return
  busy.value = true
  try {
    downloadExportBlob(
      await http.getFile(
        '/otherout/' + (detail ? 'exportDetailExcel' : 'exportEasyExcel'),
        { ids: id.value },
        { responseType: 'blob' }
      ),
      detail ? '出库明细.xlsx' : '出库汇总.xlsx'
    )
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}
</script>
<style scoped>
.inbound-workspace {
  padding: 20px;
  height: 100%;
  overflow: auto;
  box-sizing: border-box;
  background: #f5f7fa;
}
header,
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: space-between;
  margin-bottom: 16px;
}
header h2 {
  margin: 0;
}
header p {
  color: #606266;
}
.actions {
  justify-content: flex-start;
  flex-wrap: wrap;
  margin-top: 16px;
}
.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 20px;
  margin-top: 16px;
}
main,
aside {
  background: white;
  padding: 18px;
  border-radius: 8px;
  min-width: 0;
}
.header-form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.el-table {
  margin-top: 12px;
}
small,
.document span {
  display: block;
  color: #909399;
}
.total {
  text-align: right;
  font-weight: 600;
}
.document {
  display: block;
  text-align: left;
  width: 100%;
  padding: 12px;
  border: 1px solid #e4e7ed;
  background: white;
  border-radius: 6px;
  margin-top: 10px;
  cursor: pointer;
}
.document.selected {
  border-color: #409eff;
  background: #ecf5ff;
}
aside .el-button {
  margin-top: 10px;
}
@media (max-width: 1100px) {
  .workspace-grid {
    grid-template-columns: 1fr;
  }
  .header-form {
    grid-template-columns: 1fr;
  }
}
</style>
