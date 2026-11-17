<template>
  <section class="movement-workspace">
    <header>
      <h2>{{ counting ? '库存盘点' : '仓库调拨' }}</h2>
      <el-tag>{{ posted ? '已审核 · 库存已更新' : id ? '草稿 · 库存未变' : '新单据' }}</el-tag>
    </header>
    <el-alert
      :closable="false"
      type="info"
      :title="
        counting
          ? '只盘点本单列出的商品、仓库、属性和批次。保存时记录账面快照，审核才按实盘差异调整库存；快照过期须重新盘点。'
          : '同一商品从调出仓转入调入仓，审核后可在调入仓继续销售。已有下游出库时，请先撤销下游业务，再反审核调拨。'
      "
    />
    <el-alert v-if="error" type="error" :title="error" :closable="false" />
    <div class="actions">
      <el-button :disabled="busy" @click="newDocument">新建</el-button>
      <el-button type="primary" :disabled="busy || posted" @click="save">保存草稿</el-button>
      <el-button type="success" :disabled="busy || !id || dirty" @click="audit">{{
        posted ? '反审核并回滚' : counting ? '审核并调整库存' : '审核调拨'
      }}</el-button>
      <el-button type="danger" plain :disabled="busy || !id || posted || dirty" @click="remove"
        >删除草稿</el-button
      >
      <span v-if="dirty" class="hint">有未保存修改，请先保存</span>
    </div>
    <div class="layout">
      <main>
        <el-form :disabled="busy || posted" label-position="top" class="head-form">
          <el-form-item label="单据编号"
            ><el-input v-model="header.number" aria-label="单据编号" maxlength="32"
          /></el-form-item>
          <el-form-item label="业务时间"
            ><input
              v-model="header.time"
              type="datetime-local"
              aria-label="业务时间"
              step="1"
              :disabled="busy || posted"
          /></el-form-item>
          <el-form-item label="备注"
            ><el-input v-model="header.data" aria-label="备注"
          /></el-form-item>
        </el-form>
        <el-button :disabled="busy || posted" @click="picker = true">选择商品</el-button>
        <p class="hint">
          {{
            counting
              ? '实盘数量是现场实际数量，可以为0；盘盈按填写的单位成本入账，盘亏按系统实际成本出库。序列号商品需填写全部实盘序列号，一行一个。'
              : '每行分别选择调出、调入仓库，数量为商品基本单位；预计成本不会覆盖原库存实际成本。'
          }}
        </p>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>商品 / 属性 / 基本单位</th>
                <th>{{ counting ? '盘点仓库' : '调出仓库' }}</th>
                <th v-if="!counting">调入仓库</th>
                <th v-if="counting">账面数量</th>
                <th>{{ counting ? '实盘数量' : '调拨数量' }}</th>
                <th v-if="counting">差异</th>
                <th>{{ counting ? '盘盈单位成本' : '预计单位成本' }}</th>
                <th>批次 / 序列号</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in items" :key="row.id || index">
                <td>
                  <strong>{{ row.name }}</strong>
                  <div>{{ row.number }} {{ row.attr }} · {{ row.unit }}</div>
                </td>
                <td>
                  <el-select-v2
                    v-model="row.warehouse"
                    aria-label="调出或盘点仓库"
                    :disabled="busy || posted || (counting && !!row.id)"
                    filterable
                    :options="warehouseOptions"
                  />
                </td>
                <td v-if="!counting">
                  <el-select-v2
                    v-model="row.storehouse"
                    aria-label="调入仓库"
                    :disabled="busy || posted"
                    filterable
                    :options="warehouseOptions"
                  />
                </td>
                <td v-if="counting">{{ row.book_qty == null ? '保存时读取' : row.book_qty }}</td>
                <td>
                  <input
                    v-model.number="row[counting ? 'counted' : 'nums']"
                    type="number"
                    :aria-label="counting ? '实盘数量' : '调拨数量'"
                    :min="counting ? 0 : 0.0001"
                    step="0.0001"
                    :disabled="busy || posted"
                  />
                </td>
                <td v-if="counting">
                  {{
                    row.book_qty == null
                      ? '—'
                      : Number((Number(row.counted) - Number(row.book_qty)).toFixed(4))
                  }}
                </td>
                <td>
                  <span v-if="posted && !counting">{{ row.actualPrice ?? '待核对' }}</span
                  ><input
                    v-else
                    v-model.number="row.price"
                    type="number"
                    aria-label="单位成本"
                    min="0"
                    step="0.0001"
                    :disabled="busy || posted"
                  />
                </td>
                <td>
                  <template v-if="row.batchEnabled"
                    ><el-input
                      v-model="row.batch"
                      placeholder="批次号"
                      aria-label="批次号"
                      :disabled="busy || posted || (counting && !!row.id)" /><input
                      v-model="row.mfd"
                      type="date"
                      aria-label="生产日期"
                      :disabled="busy || posted || (counting && !!row.id)" /></template
                  ><el-input
                    v-if="row.serialEnabled"
                    v-model="row.serialText"
                    type="textarea"
                    placeholder="每行一个实物序列号"
                    aria-label="实物序列号"
                    :disabled="busy || posted"
                  />
                </td>
                <td>
                  <el-button
                    link
                    type="danger"
                    :disabled="busy || posted"
                    @click="items.splice(index, 1)"
                    >移除</el-button
                  >
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <el-empty v-if="!items.length" description="先选择商品，再填写仓库和数量" />
        <div v-if="counting && adjustments.length" class="adjustments">
          <h3>已入账差异单</h3>
          <p v-for="link in adjustments" :key="link.document_id">
            {{ link.kind === 'entry' ? '盘盈入库' : '盘亏出库' }}：{{
              link.document_id
            }}（由此盘点单统一反审核）
          </p>
        </div>
      </main>
      <aside>
        <h3>已保存单据</h3>
        <el-input
          v-model="keyword"
          placeholder="按单号查询"
          aria-label="查询单号"
          @keyup.enter="search"
        /><el-button @click="search">查询</el-button
        ><button
          v-for="doc in documents"
          :key="doc.id"
          class="document"
          :disabled="busy"
          @click="open(doc.id)"
        >
          <strong>{{ doc.number }}</strong
          ><span>{{
            Number(counting ? doc.state : doc.examine) === 1 ? '已审核' : '草稿'
          }}</span></button
        ><el-pagination
          v-model:current-page="page"
          :page-size="20"
          :total="total"
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
import { extractApiErrorMessage } from '@/utils/formValidation'
import OperationPopTable from '@/components/operationpoptable/OperationPopTable.vue'
const props = defineProps<{ kind: 'transfer' | 'count' }>()
type Row = Record<string, any>
const counting = computed(() => props.kind === 'count')
const base = computed(() =>
  counting.value ? '/j2-store/verify/documents' : '/j2-store/transfer/documents'
)
const http = useHttp(),
  route = useRoute(),
  router = useRouter()
const header = reactive<Row>({}),
  items = ref<Row[]>([]),
  warehouses = ref<Row[]>([]),
  documents = ref<Row[]>([]),
  adjustments = ref<Row[]>([])
const warehouseOptions = computed(() =>
  warehouses.value.map((w) => ({
    value: String(w.id),
    label: `${w.name}${w.number ? ' · ' + w.number : ''}`
  }))
)
const id = ref(''),
  version = ref(''),
  keyword = ref(''),
  error = ref(''),
  busy = ref(false),
  picker = ref(false),
  page = ref(1),
  total = ref(0)
let original = ''
const signature = () => JSON.stringify([header, items.value])
const dirty = computed(() => original !== signature())
const posted = computed(() => Number(counting.value ? header.state : header.examine) === 1)
function localTime(value: any) {
  const d = new Date(typeof value === 'number' ? value : String(value).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) throw Error('单据时间无效')
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
function unwrap(r: any) {
  if (r.code !== 10000 || r.data == null) throw Error(r.message || '操作失败')
  return r.data
}
function fail(e: any) {
  if (e !== 'cancel' && e !== 'close')
    error.value = extractApiErrorMessage(e, '操作失败，请刷新后重试')
}
function reset() {
  Object.keys(header).forEach((k) => delete header[k])
  Object.assign(header, {
    number: (counting.value ? 'PD' : 'DB') + Date.now() + Math.random().toString(16).slice(2, 6),
    time: localTime(Date.now()),
    data: ''
  })
  id.value = ''
  version.value = ''
  items.value = []
  adjustments.value = []
  error.value = ''
  original = signature()
}
async function discard() {
  if (dirty.value)
    await ElMessageBox.confirm('当前修改尚未保存，是否放弃？', '切换单据', { type: 'warning' })
}
async function newDocument() {
  try {
    await discard()
    reset()
    await router.replace({ query: route.query.kind ? { kind: route.query.kind } : {} })
  } catch (e) {
    fail(e)
  }
}
async function loadList() {
  const r = unwrap(
    await http.get(base.value, { pageIndex: page.value, pageSize: 20, number: keyword.value })
  )
  documents.value = r.rows
  total.value = r.total
}
async function search() {
  try {
    page.value = 1
    await loadList()
  } catch (e) {
    fail(e)
  }
}
async function reload() {
  const r = unwrap(await http.get(`${base.value}/${id.value}`))
  Object.keys(header).forEach((k) => delete header[k])
  Object.assign(header, r.header, { time: localTime(r.header.time) })
  version.value = r.version
  adjustments.value = r.adjustments || []
  items.value = r.items.map((row: Row) => {
    const p = r.goods.find((g: Row) => String(g.id) === String(row.goods)) || {}
    return {
      ...row,
      name: p.name || row.goods,
      number: p.number,
      nums: Number(row.nums),
      counted: Number(row.counted),
      price: Number(row.price),
      batchEnabled: Number(p.batch) === 1,
      serialEnabled: Number(p.serial) === 1,
      mfd: row.mfd ? String(row.mfd).slice(0, 10) : null,
      serialText: JSON.parse(row.serial || '[]').join('\n')
    }
  })
  original = signature()
}
async function open(identifier: string) {
  try {
    await discard()
    busy.value = true
    error.value = ''
    id.value = identifier
    await reload()
    await router.replace({ query: { ...route.query, id: identifier } })
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}
function choose(products: Row[]) {
  for (const p of products) {
    let unit = String(p.unit || '')
    if (unit === '-1') unit = String(JSON.parse(p.units || '[]')[0]?.source || '')
    items.value.push({
      goods: String(p.id),
      name: p.name,
      number: p.number || p.code,
      attr: p.selectedAttr || '',
      unit,
      warehouse: '',
      storehouse: '',
      nums: Number(p.quantity || 1),
      counted: null,
      price: Number(p.purchasePrice ?? p.buy ?? 0),
      batch: '',
      mfd: null,
      serialText: '',
      batchEnabled: Number(p.batch) === 1,
      serialEnabled: Number(p.serial) === 1
    })
  }
  picker.value = false
}
function payload() {
  if (!items.value.length) throw Error('请先选择商品')
  return {
    id: id.value || undefined,
    version: version.value || undefined,
    number: header.number,
    time: header.time.replace('T', ' '),
    data: header.data,
    items: items.value.map((row) => ({
      ...row,
      serial: JSON.stringify(
        String(row.serialText || '')
          .split(/\r?\n/)
          .map((s) => s.trim())
          .filter(Boolean)
      ),
      mfd: row.mfd || null
    }))
  }
}
async function save() {
  try {
    busy.value = true
    error.value = ''
    id.value = unwrap(await http.post(base.value, payload()))
    await reload()
    await router.replace({ query: { ...route.query, id: id.value } })
    await loadList()
    ElMessage.success(
      counting.value ? '盘点快照和实盘数量已保存，尚未调整库存' : '调拨草稿已保存，尚未移动库存'
    )
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}
async function audit() {
  try {
    await ElMessageBox.confirm(
      posted.value
        ? '将撤回本单原库存影响；有后续销售或出库时须先撤销后续业务。'
        : counting.value
          ? '将按当前盘点快照和实盘数量入账差异，是否继续？'
          : '将从调出仓扣减并向调入仓增加库存，是否继续？',
      '确认库存操作',
      { type: 'warning' }
    )
    busy.value = true
    error.value = ''
    const target = posted.value ? 0 : 1
    unwrap(
      await http.post(
        counting.value ? `${base.value}/${id.value}/audit` : `${base.value}/audit`,
        counting.value
          ? { target, version: version.value }
          : { target, ids: [id.value], versions: { [id.value]: version.value } }
      )
    )
    await reload()
    await loadList()
    ElMessage.success('库存操作已完成')
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}
async function remove() {
  try {
    await ElMessageBox.confirm('删除未审核草稿，保留操作历史，是否继续？', '删除草稿', {
      type: 'warning'
    })
    busy.value = true
    unwrap(
      await http.post(
        counting.value ? `${base.value}/${id.value}/delete` : `${base.value}/delete`,
        counting.value
          ? { version: version.value }
          : { ids: [id.value], versions: { [id.value]: version.value } }
      )
    )
    reset()
    await router.replace({ query: route.query.kind ? { kind: route.query.kind } : {} })
    await loadList()
  } catch (e) {
    fail(e)
  } finally {
    busy.value = false
  }
}
onMounted(async () => {
  reset()
  try {
    warehouses.value = unwrap(await http.get(`${base.value}/options`)).warehouses
    if (typeof route.query.id === 'string') {
      id.value = route.query.id
      await reload()
    }
    await loadList()
  } catch (e) {
    fail(e)
  }
})
</script>

<style scoped>
.movement-workspace {
  padding: 22px;
  background: #f5f7fb;
  min-height: 100%;
}
header,
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
header h2 {
  margin: 0;
  flex: 1;
}
.el-alert {
  margin-bottom: 14px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 270px;
  gap: 18px;
}
main,
aside {
  background: white;
  border-radius: 10px;
  padding: 18px;
}
.head-form {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
}
.hint {
  color: #64748b;
  font-size: 13px;
}
.table-scroll {
  overflow: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  padding: 12px;
  min-width: 145px;
}
th {
  background: #f1f5f9;
}
td div {
  font-size: 12px;
  color: #64748b;
}
input {
  font: inherit;
  padding: 8px;
  border: 1px solid #cbd5e1;
  border-radius: 5px;
  width: 100%;
  box-sizing: border-box;
}
input:disabled {
  background: #f1f5f9;
}
.document {
  display: flex;
  flex-direction: column;
  gap: 7px;
  text-align: left;
  width: 100%;
  padding: 12px;
  margin-top: 10px;
  border: 1px solid #dbe3ed;
  border-radius: 7px;
  background: white;
  cursor: pointer;
}
.document span {
  color: #64748b;
}
.adjustments {
  margin-top: 20px;
  overflow-wrap: anywhere;
}
@media (max-width: 1050px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .head-form {
    grid-template-columns: 1fr;
  }
}
</style>
