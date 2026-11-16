<template>
  <div class="return-workspace">
    <el-alert title="保存和核对不改变库存或资金。审核将从原仓库出库、记录供应商退款到账并冲减应付；请先核对商品、数量、序列号和退款账户。" type="info" :closable="false" show-icon />
    <el-tabs v-model="tab">
      <el-tab-pane label="从采购单开退货草稿" name="source">
        <p class="guide">① 查询已审核采购单　② 选择退货商品与数量　③ 保存后重新打开核对</p>
        <form class="return-search" @submit.prevent="sourcePage = 1; loadSources()">
          <el-input v-model="sourceNumber" placeholder="输入来源采购单编号" clearable aria-label="来源采购单编号" />
          <el-input v-model="sourceSupplier" placeholder="输入供应商名称或编号" clearable aria-label="来源供应商" />
          <el-button type="primary" native-type="submit" :loading="sourceLoading">查询采购单</el-button>
        </form>
        <el-alert v-if="sourceError" :title="sourceError" type="error" :closable="false"><el-button @click="loadSources">重新查询采购单</el-button></el-alert>
        <el-table :data="sources" v-loading="sourceLoading" border empty-text="没有符合条件的已审核采购单">
          <el-table-column prop="number" label="来源采购单" min-width="210" />
          <el-table-column prop="supplierName" label="供应商" min-width="160" />
          <el-table-column prop="time" label="采购日期" min-width="160" />
          <el-table-column prop="actual" label="含税金额" width="130" />
          <el-table-column label="操作" width="150"><template #default="{ row }"><el-button link type="primary" :disabled="editorLoading || busy" @click="startSource(row.id)">选择此来源</el-button></template></el-table-column>
        </el-table>
        <el-pagination layout="prev,pager,next,total" :current-page="sourcePage" :page-size="10" :total="sourceTotal" @current-change="sourcePage = $event; loadSources()" />
      </el-tab-pane>
      <el-tab-pane label="已保存退货单" name="saved">
        <form class="return-search" @submit.prevent="savedPage = 1; loadSaved()">
          <el-input v-model="returnNumber" placeholder="输入退货单编号" clearable aria-label="退货单查询编号" />
          <el-input v-model="returnSupplier" placeholder="输入供应商名称或编号" clearable aria-label="退货供应商" />
          <el-button type="primary" native-type="submit" :loading="savedLoading">查询退货单</el-button>
          <el-button @click="loadSaved">刷新退货列表</el-button>
          <el-button :disabled="!selectedSaved.length || busy || savedLoading" @click="reviewSelected(1)">核对选中</el-button>
          <el-button :disabled="!selectedSaved.length || busy || savedLoading" @click="reviewSelected(0)">反核对选中</el-button>
          <el-button type="success" :disabled="!selectedSaved.length || busy || savedLoading" @click="postSelected(1)">审核选中</el-button>
          <el-button type="warning" :disabled="!selectedSaved.length || busy || savedLoading" @click="postSelected(0)">反审核选中</el-button>
        </form>
        <el-alert v-if="savedError" :title="savedError" type="error" :closable="false"><el-button @click="loadSaved">重新查询退货单</el-button></el-alert>
        <el-table :data="savedRows" row-key="id" v-loading="savedLoading" border empty-text="尚无符合条件的退货单，可先从已审核采购单开草稿" @selection-change="selectedSaved = $event">
          <el-table-column type="selection" width="48" />
          <el-table-column prop="number" label="退货单编号" min-width="210" />
          <el-table-column prop="sourceNumber" label="来源采购单" min-width="200" />
          <el-table-column prop="supplierName" label="供应商" min-width="150" />
          <el-table-column prop="timeText" label="退货日期" min-width="165" />
          <el-table-column prop="actual" label="含税金额" width="120" />
          <el-table-column prop="money" label="计划退款" width="110" />
          <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="Number(row.examine) === 1 ? 'success' : 'info'">{{ Number(row.examine) === 1 ? '已审核' : Number(row.check) === 1 ? '已核对' : '草稿' }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="170" fixed="right"><template #default="{ row }"><el-button link type="primary" :disabled="busy || editorLoading" @click="openReturn(row.id)">查看 / 修改</el-button><el-button link type="danger" :disabled="busy" @click="removeRow(row)">删除</el-button></template></el-table-column>
        </el-table>
        <el-pagination layout="prev,pager,next,total" :current-page="savedPage" :page-size="10" :total="savedTotal" @current-change="savedPage = $event; loadSaved()" />
      </el-tab-pane>
    </el-tabs>
    <el-alert v-if="entryError" :title="entryError" type="error" :closable="false" />
    <el-dialog v-model="editorVisible" :title="savedId ? '采购退货单详情' : '新建采购退货草稿'" width="1100px" top="4vh" :close-on-click-modal="false" :close-on-press-escape="!busy" :show-close="!busy">
      <div class="editor-scroll">
      <el-alert v-if="editorError" :title="editorError" type="error" :closable="false" show-icon><el-button v-if="savedId" :disabled="busy" @click="openReturn(savedId)">重新读取草稿</el-button></el-alert>
      <el-alert v-if="readOnly" :title="approved ? '已审核单据为只读。如需修改，请先反审核，再反核对。' : checked ? '已核对单据为只读。如需修改，请先反核对，再保存修改。' : '当前无法编辑，请按上方提示处理后重新读取草稿。'" type="info" :closable="false" />
      <p class="source-caption">来源：{{ sourceLabel }}　供应商：{{ supplierLabel }} <el-tag v-if="savedId" :type="approved ? 'success' : 'info'">{{ approved ? '已审核' : checked ? '已核对' : '已保存' }}</el-tag></p>
      <el-form label-position="top" :disabled="busy || readOnly || editorLoading" class="draft-fields">
        <el-form-item label="退货单编号" required><el-input v-model="form.number" maxlength="32" aria-label="退货单编号" /></el-form-item>
        <el-form-item label="退货日期" required><el-date-picker v-model="form.time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="选择退货日期" /></el-form-item>
        <el-form-item :label="approved ? '已入账退款金额' : '计划退款金额'"><el-input v-model.number="form.money" type="number" min="0" step="0.0001" aria-label="计划退款金额" /></el-form-item>
        <el-form-item label="单据费用"><el-input v-model.number="form.cost" type="number" min="0" step="0.0001" aria-label="单据费用" /></el-form-item>
        <el-form-item :label="form.money > 0 ? '退款账户（必选）' : '退款账户（无退款可不选）'"><el-select v-model="form.account" filterable remote clearable :remote-method="searchAccounts" :loading="accountLoading" placeholder="按账户名称或编号搜索" aria-label="退款账户"><el-option v-for="account in accounts" :key="account.id" :value="account.id" :label="`${account.name} ${account.number || ''}`" /></el-select></el-form-item>
      </el-form>
      <el-alert v-if="accountError" :title="accountError" type="error" :closable="false" />
      <el-table :data="rows" border max-height="360">
        <el-table-column label="退货" width="70"><template #default="{ row }"><el-checkbox v-model="row.selected" :disabled="busy || readOnly" :aria-label="`退货 ${row.goodsName}`" /></template></el-table-column>
        <el-table-column prop="goodsName" label="来源商品" min-width="150" />
        <el-table-column prop="warehouseName" label="原入库仓库" min-width="150" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column label="退货数量" width="180"><template #default="{ row }"><el-input v-model.number="row.quantity" type="number" min="0" step="0.0001" :disabled="busy || readOnly" :aria-label="`退货数量 ${row.goodsName}`" /></template></el-table-column>
        <el-table-column prop="available" label="读取时可退" width="110" />
        <el-table-column prop="price" label="来源单价" width="110" />
        <el-table-column label="预计含税金额" width="140"><template #default="{ row }">{{ estimate(row).toFixed(4) }}</template></el-table-column>
      </el-table>
      <section v-if="rows.some(row => row.selected && (row.serialRequired || row.serialSelection.length))" aria-label="退回原采购序列号">
        <h3>选择退回的原采购序列号</h3>
        <div v-for="row in rows.filter(item => item.selected && (item.serialRequired || item.serialSelection.length))" :key="row.source">
          <p>{{ row.goodsName }} · 已选 {{ row.serialSelection.length }} 个<span v-if="!readOnly && serialCount(row) !== null">，当前退货数量需要 {{ serialCount(row) }} 个</span></p>
          <el-select v-model="row.serialSelection" multiple filterable :disabled="busy || readOnly || editorLoading" :aria-label="`退货序列号 ${row.goodsName}`" placeholder="选择实际退回的原采购序列号" style="width:100%"><el-option v-for="number in readOnly ? row.serialSelection : (row.availableSerials || [])" :key="number" :label="number" :value="number" /></el-select>
          <p v-if="!readOnly && serialCount(row) === null" role="alert">当前退货数量不能换算为整数个序列号，请先调整数量。</p>
        </div>
      </section>
      <p>选中明细预计含税合计：{{ estimatedTotal }}。保存后以重新读取的金额为准。</p>
      <p class="guide">商品、仓库、单位和价格来自原采购单。取消勾选可不退该行；保存时会重新检查可退数量并计算金额。</p>
      <el-form label-position="top" :disabled="busy || readOnly"><el-form-item label="退货备注"><el-input v-model="form.data" type="textarea" maxlength="256" show-word-limit /></el-form-item></el-form>
      </div>
      <template #footer><el-button :disabled="busy" @click="editorVisible = false">关闭</el-button><el-button v-if="savedId && !approved" :loading="busy" :disabled="busy || editorLoading || !version" @click="reviewCurrent">{{ checked ? '反核对退货单' : '核对退货单' }}</el-button><el-button v-if="savedId && (checked || approved)" :type="approved ? 'warning' : 'success'" :disabled="busy || editorLoading || !version" @click="postCurrent">{{ approved ? '反审核退货单' : '审核并入账' }}</el-button><el-button type="primary" :loading="busy" :disabled="readOnly || editorLoading || (savedId !== '' && version === '')" @click="save">{{ savedId ? '保存草稿修改' : '保存退货草稿' }}</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PurchaseNoteAPI } from '@/apis/purchase/purchaseOrder'
import { purchaseReturnSourceApi } from '@/apis/purchase/returnSource'
import { returnDraftApi } from '@/apis/purchase/returnDraft'
import type { ReturnDraftInput } from '@/apis/purchase/returnDraft'
import { extractApiErrorMessage } from '@/utils/formValidation'

const route = useRoute()
const router = useRouter()
const tab = ref(route.name === 'SalesReturnReport' || typeof route.query.draft === 'string' ? 'saved' : 'source')
const sourceNumber = ref(''), sourceSupplier = ref(''), sourcePage = ref(1), sourceTotal = ref(0), sources = ref<Record<string, any>[]>([]), sourceLoading = ref(false), sourceError = ref('')
const returnNumber = ref(''), returnSupplier = ref(''), savedPage = ref(1), savedTotal = ref(0), savedRows = ref<Record<string, any>[]>([]), savedLoading = ref(false), savedError = ref('')
const entryError = ref(''), editorError = ref(''), editorVisible = ref(false), editorLoading = ref(false), busy = ref(false)
const savedId = ref(''), version = ref(''), sourceId = ref(''), sourceVersion = ref(''), sourceLabel = ref(''), supplierLabel = ref(''), readOnly = ref(false)
const rows = ref<Record<string, any>[]>([]), accounts = ref<Record<string, any>[]>([]), accountLoading = ref(false), accountError = ref('')
const selectedSaved = ref<Record<string, any>[]>([]), checked = ref(false), approved = ref(false), savedSnapshot = ref('')
const form = reactive({ number: '', time: '', money: 0, cost: 0, account: '', data: '' })
let sourceSequence = 0, savedSequence = 0, editorSequence = 0, accountSequence = 0
function estimate(row: Record<string, any>) { const quantity = Number(row.quantity), original = Number(row.nums); return Number.isFinite(quantity) && original > 0 ? Math.round(Number(row.tpt || 0) * quantity / original * 10000) / 10000 : 0 }
const estimatedTotal = computed(() => rows.value.filter(row => row.selected).reduce((total, row) => total + estimate(row), 0).toFixed(4))
function serialSelection(raw: any): string[] { const values = typeof raw === 'string' ? JSON.parse(raw || '[]') : raw || []; if (!Array.isArray(values)) throw new Error('序列号记录格式不正确，请先核对原单据'); return values.map(value => typeof value === 'string' ? value : String(value.number || '')) }
function serialCount(row: Record<string, any>): number | null { const count = Number(row.quantity) * Number(row.sourceBaseQuantity) / Number(row.sourceQuantity); return Number.isFinite(count) && count > 0 && Math.abs(count - Math.round(count)) < .00000001 ? Math.round(count) : null }
function editorSnapshot() { return JSON.stringify({ form, rows: rows.value.map(row => ({ id: row.id, source: row.source, quantity: row.quantity, selected: row.selected, serial: row.serialSelection, data: row.data })) }) }
const dirty = computed(() => !!savedSnapshot.value && editorSnapshot() !== savedSnapshot.value)
async function loadSources() {
  const sequence = ++sourceSequence; sourceLoading.value = true; sourceError.value = ''
  try { const result = await PurchaseNoteAPI.getList({ pageIndex: sourcePage.value, pageSize: 10, number: sourceNumber.value.trim() || undefined, supplier: sourceSupplier.value.trim() || undefined, examine: 1 }); if (sequence !== sourceSequence) return; if (result.code !== 10000 || !Array.isArray(result.data?.rows)) throw new Error(result.message || '采购单查询失败'); sources.value = result.data.rows; sourceTotal.value = Number(result.data.total) }
  catch (error) { if (sequence === sourceSequence) { sources.value = []; sourceTotal.value = 0; sourceError.value = extractApiErrorMessage(error) } }
  finally { if (sequence === sourceSequence) sourceLoading.value = false }
}
async function loadSaved() {
  const sequence = ++savedSequence; savedLoading.value = true; savedError.value = ''
  try { const result = await returnDraftApi.list({ pageIndex: savedPage.value, pageSize: 10, number: returnNumber.value.trim() || undefined, supplier: returnSupplier.value.trim() || undefined }); if (sequence !== savedSequence) return; selectedSaved.value = []; savedRows.value = result.rows || []; savedTotal.value = Number(result.total) }
  catch (error) { if (sequence === savedSequence) { savedRows.value = []; savedTotal.value = 0; savedError.value = extractApiErrorMessage(error) } }
  finally { if (sequence === savedSequence) savedLoading.value = false }
}
function today() { return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).format(new Date()) }
async function startSource(id: string, expectedVersion?: string) {
  accountSequence++; accountLoading.value = false
  const sequence = ++editorSequence; editorLoading.value = true; entryError.value = ''
  try {
    const document = await PurchaseNoteAPI.getDocument(id), preview = await purchaseReturnSourceApi.preview(id)
    if (sequence !== editorSequence) return
    if (document.code !== 10000 || !document.data) throw new Error(document.message || '来源采购单读取失败')
    if (preview.source !== id || preview.sourceVersion !== document.data.version || (expectedVersion && expectedVersion !== preview.sourceVersion)) throw new Error('来源采购单已变化，请重新查询并核对后选择')
    savedId.value = ''; version.value = ''; sourceId.value = id; sourceVersion.value = preview.sourceVersion; sourceLabel.value = preview.sourceNumber; supplierLabel.value = document.data.header.supplierName || preview.supplier
    rows.value = preview.items.map(item => ({ ...item, serialSelection: serialSelection(item.serial), selected: true, quantity: item.available }))
    Object.assign(form, { number: 'CGTH' + Date.now(), time: today(), money: 0, cost: 0, account: '', data: '' })
    accounts.value = []; editorError.value = ''; accountError.value = ''; readOnly.value = false; checked.value = false; approved.value = false; savedSnapshot.value = ''; editorVisible.value = true; void searchAccounts('')
  } catch (error) { if (sequence === editorSequence) entryError.value = extractApiErrorMessage(error) }
  finally { if (sequence === editorSequence) editorLoading.value = false }
}
async function openReturn(id: string) {
  accountSequence++; accountLoading.value = false
  const sequence = ++editorSequence; editorLoading.value = true; entryError.value = ''
  try {
    const document = await returnDraftApi.document(id); if (sequence !== editorSequence) return
    const head = document.header
    savedId.value = id; version.value = document.version; sourceId.value = String(head.source); sourceVersion.value = document.sourceVersion; sourceLabel.value = head.sourceNumber || String(head.source); supplierLabel.value = head.supplierName || String(head.supplier)
    rows.value = document.items.map(item => ({ ...item, serialSelection: serialSelection(item.serial), selected: true, quantity: Number(item.nums), available: '保存时复核' }))
    Object.assign(form, { number: head.number, time: head.timeText, money: Number(head.money), cost: Number(head.cost || 0), account: head.account || '', data: head.data || '' })
    accounts.value = head.account ? [{ id: String(head.account), name: head.accountName || String(head.account) }] : []
    readOnly.value = Number(head.examine) !== 0 || Number(head.check) !== 0 || Number(head.nucleus) !== 0
    checked.value = Number(head.check) === 1; approved.value = Number(head.examine) !== 0; savedSnapshot.value = editorSnapshot()
    editorError.value = ''; accountError.value = ''; editorVisible.value = true
    if (!readOnly.value) {
      let options: Awaited<ReturnType<typeof returnDraftApi.sourceOptions>>
      try { options = await returnDraftApi.sourceOptions(id) }
      catch (error) { if (sequence === editorSequence) { readOnly.value = true; editorError.value = '编辑来源选项读取失败：' + extractApiErrorMessage(error) } return }
      if (sequence !== editorSequence) return
      if (options.version !== document.version || options.sourceVersion !== document.sourceVersion || rows.value.some(row => !options.items.some(item => item.source === row.source))) { version.value = ''; readOnly.value = true; throw new Error('退货单或来源已变化，请重新读取草稿后核对') }
      rows.value = rows.value.map(row => { const source = options.items.find(item => item.source === row.source)!; return { ...row, serialRequired: source.serialRequired, availableSerials: source.availableSerials || [], sourceBaseQuantity: source.sourceBaseQuantity, sourceQuantity: source.sourceQuantity, available: source.available } })
      void searchAccounts('')
    }
  } catch (error) { if (sequence === editorSequence) { const message = extractApiErrorMessage(error); if (editorVisible.value) editorError.value = message; else entryError.value = message } }
  finally { if (sequence === editorSequence) editorLoading.value = false }
}
async function searchAccounts(keyword: string) {
  if (!sourceId.value) return
  const sequence = ++accountSequence; accountLoading.value = true; accountError.value = ''
  try { const result = await returnDraftApi.accounts(sourceId.value, keyword, !!savedId.value, savedId.value || undefined); if (sequence === accountSequence) { const current = accounts.value.filter(item => item.id === form.account); accounts.value = [...current, ...result.filter(item => !current.some(existing => existing.id === item.id))] } }
  catch (error) { if (sequence === accountSequence) accountError.value = extractApiErrorMessage(error) }
  finally { if (sequence === accountSequence) accountLoading.value = false }
}
async function save() {
  if (busy.value || editorLoading.value || readOnly.value || (savedId.value && !version.value)) return
  editorError.value = ''
  const selected = rows.value.filter(row => row.selected)
  if (!form.number.trim() || !form.time || !selected.length || selected.some(row => !Number.isFinite(Number(row.quantity)) || Number(row.quantity) <= 0)) { editorError.value = '请填写编号、退货日期，并勾选至少一条数量大于零的明细'; return }
  if (form.money > 0 && !form.account) { editorError.value = '填写计划退款金额时请选择退款账户'; return }
  if (selected.some(row => row.serialRequired && (serialCount(row) === null || new Set(row.serialSelection).size !== row.serialSelection.length || row.serialSelection.some((number: string) => !row.availableSerials?.includes(number)) || serialCount(row) !== row.serialSelection.length))) { editorError.value = '请按退货基础数量选择可用的原采购序列号'; return }
  const input: ReturnDraftInput = { id: savedId.value || undefined, version: version.value || undefined, source: sourceId.value, sourceVersion: sourceVersion.value, number: form.number.trim(), time: form.time, money: Number(form.money || 0), cost: Number(form.cost || 0), account: form.account, data: form.data, details: selected.map(row => ({ id: savedId.value ? row.id : undefined, source: row.source, nums: Number(row.quantity), serial: JSON.stringify(row.serialSelection), data: row.data || '' })) }
  busy.value = true
  try {
    const id = await returnDraftApi.save(input); savedId.value = id; version.value = ''
    returnNumber.value = input.number; savedPage.value = 1; tab.value = 'saved'
    await openReturn(id)
    if (!version.value) editorError.value = '草稿已保存，详情读取失败：' + (editorError.value || '请重新读取草稿；不要重复新增')
    else ElMessage.success('退货草稿已保存，未出库或收取退款')
    await loadSaved()
    await router.replace({ path: route.path, query: { draft: id } })
  } catch (error) { editorError.value = extractApiErrorMessage(error) }
  finally { busy.value = false }
}
async function removeRow(row: Record<string, any>) {
  if (busy.value) return
  const id = String(row.id), reviewed = String(row.version || '')
  const sequence = savedSequence
  try { await ElMessageBox.confirm(`永久删除自由草稿【${row.number}】及明细？已核对、审核或存在关联记录的单据会被拒绝。`, '删除退货草稿', { type: 'warning' }) } catch { return }
  if (busy.value || sequence !== savedSequence) return
  busy.value = true
  try { await returnDraftApi.remove(id, reviewed); await loadSaved(); ElMessage.success('退货草稿已删除，可退数量已释放') }
  catch (error) { savedError.value = extractApiErrorMessage(error) }
  finally { busy.value = false }
}
async function reviewCurrent() {
  if (busy.value || editorLoading.value || !savedId.value || !version.value || approved.value) return
  if (dirty.value) { editorError.value = '请先保存未提交的修改，再重新核对退货单'; return }
  const id = savedId.value, reviewed = version.value, target = checked.value ? 0 : 1
  try { await ElMessageBox.confirm(target ? '核对当前显示版本的退货单？不会出库或记录供应商退款。' : '反核对后可继续修改草稿，不会变更库存或资金。', '核对采购退货单', { type: 'warning' }) } catch { return }
  if (busy.value || !editorVisible.value || id !== savedId.value || reviewed !== version.value) return
  if (dirty.value) { editorError.value = '确认期间内容已变化，请先保存后重新核对'; return }
  busy.value = true
  try { await returnDraftApi.review([id], target, reviewed); await openReturn(id); await loadSaved(); ElMessage.success(target ? '退货单已核对，未出库或收取退款' : '退货单已反核对') }
  catch (error) { editorError.value = extractApiErrorMessage(error) }
  finally { busy.value = false }
}
async function reviewSelected(target: 0 | 1) {
  if (busy.value || savedLoading.value || !selectedSaved.value.length) return
  const selection = [...selectedSaved.value], ids = selection.map(row => String(row.id)), versions = Object.fromEntries(selection.map(row => [String(row.id), String(row.version || '')]))
  if (selection.some(row => !/^[0-9a-f]{64}$/.test(String(row.version || '')))) { savedError.value = '选中单据缺少版本，请刷新列表后重新选择'; return }
  const sequence = savedSequence, selectionKey = JSON.stringify(selection.map(row => [row.id, row.version]))
  try { await ElMessageBox.confirm(`将${target ? '核对' : '反核对'}选中的${ids.length}张退货单，任一版本变化则整批取消；不会出库或收取退款。`, '批量核对退货单', { type: 'warning' }) } catch { return }
  if (busy.value || savedLoading.value || sequence !== savedSequence || JSON.stringify(selectedSaved.value.map(row => [row.id, row.version])) !== selectionKey) return
  busy.value = true
  try { await returnDraftApi.review(ids, target, versions); await loadSaved(); ElMessage.success('选中退货单核对状态已处理，未出库或收取退款') }
  catch (error) { savedError.value = extractApiErrorMessage(error) }
  finally { busy.value = false }
}
async function postCurrent() {
  if (busy.value || editorLoading.value || !savedId.value || !version.value || (!checked.value && !approved.value)) return
  if (dirty.value) { editorError.value = '请先保存修改并重新核对，再审核退货单'; return }
  const id = savedId.value, reviewed = version.value, target = approved.value ? 0 : 1
  try { await ElMessageBox.confirm(target ? '审核将从原仓库实际出库、记录供应商退款到账并冲减应付。确认当前商品、数量、序列号和退款账户正确？' : '反审核将按本次入账凭据恢复库存，并撤销供应商退款和应付变化。确认继续？', '采购退货入账', { type: 'warning' }) } catch { return }
  if (busy.value || !editorVisible.value || id !== savedId.value || reviewed !== version.value || dirty.value) return
  busy.value = true
  try { await returnDraftApi.post([id], target, reviewed); await openReturn(id); await loadSaved(); ElMessage.success(target ? '采购退货已审核入账' : '采购退货已反审核，仍为已核对状态') }
  catch (error) { editorError.value = extractApiErrorMessage(error) }
  finally { busy.value = false }
}
async function postSelected(target: 0 | 1) {
  if (busy.value || savedLoading.value || !selectedSaved.value.length) return
  const selection = [...selectedSaved.value], ids = selection.map(row => String(row.id)), versions = Object.fromEntries(selection.map(row => [String(row.id), String(row.version || '')]))
  if (selection.some(row => !/^[0-9a-f]{64}$/.test(String(row.version || '')))) { savedError.value = '选中单据缺少版本，请刷新列表后重新选择'; return }
  const sequence = savedSequence, selectionKey = JSON.stringify(selection.map(row => [row.id, row.version]))
  try { await ElMessageBox.confirm(`将${target ? '审核' : '反审核'}选中的${ids.length}张退货单，实际联动库存、供应商退款和应付；任一版本变化或业务失败则整批取消。`, '批量采购退货入账', { type: 'warning' }) } catch { return }
  if (busy.value || savedLoading.value || sequence !== savedSequence || JSON.stringify(selectedSaved.value.map(row => [row.id, row.version])) !== selectionKey) return
  busy.value = true
  try { await returnDraftApi.post(ids, target, versions); await loadSaved(); ElMessage.success('选中采购退货单入账状态已处理') }
  catch (error) { savedError.value = extractApiErrorMessage(error) }
  finally { busy.value = false }
}
onMounted(() => { void loadSources(); void loadSaved(); if (typeof route.query.draft === 'string') void openReturn(route.query.draft); else if (typeof route.query.source === 'string') void startSource(route.query.source, typeof route.query.sourceVersion === 'string' ? route.query.sourceVersion : undefined) })
onBeforeUnmount(() => { sourceSequence++; savedSequence++; editorSequence++; accountSequence++ })
</script>

<style scoped>
.return-workspace { padding: 20px; background: #fff; border-radius: 8px; }
.return-search { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.return-search .el-input { width: 260px; }
.guide { color: #667085; margin: 14px 0; line-height: 1.7; }
.draft-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 20px; }
.source-caption { margin: 16px 0; color: #344054; }
.editor-scroll { max-height: 70vh; overflow: auto; padding-right: 8px; }
.el-pagination { margin-top: 18px; }
@media(max-width: 700px) { .draft-fields { grid-template-columns: 1fr; } }
</style>
