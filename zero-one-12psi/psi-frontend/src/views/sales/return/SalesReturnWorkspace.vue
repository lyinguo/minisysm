<template>
  <div class="return-workspace">
    <el-alert title="退货草稿保存后占用可退数量；保存不会入库或扣款。核对、审核及退款流程仍在维护中。" type="info" :closable="false" show-icon />
    <el-tabs v-model="tab">
      <el-tab-pane label="从销售单开退货草稿" name="source">
        <p class="guide">① 查询已审核销售单　② 选择退货商品与数量　③ 保存后重新打开核对</p>
        <form class="return-search" @submit.prevent="sourcePage = 1; loadSources()">
          <el-input v-model="sourceNumber" placeholder="输入来源销售单编号" clearable aria-label="来源销售单编号" />
          <el-input v-model="sourceCustomer" placeholder="输入客户名称或编号" clearable aria-label="来源客户" />
          <el-button type="primary" native-type="submit" :loading="sourceLoading">查询销售单</el-button>
        </form>
        <el-alert v-if="sourceError" :title="sourceError" type="error" :closable="false"><el-button @click="loadSources">重新查询销售单</el-button></el-alert>
        <el-table :data="sources" v-loading="sourceLoading" border empty-text="没有符合条件的已审核销售单">
          <el-table-column prop="number" label="来源销售单" min-width="210" />
          <el-table-column prop="customerName" label="客户" min-width="160" />
          <el-table-column prop="time" label="销售日期" min-width="160" />
          <el-table-column prop="actual" label="含税金额" width="130" />
          <el-table-column label="操作" width="150"><template #default="{ row }"><el-button link type="primary" :disabled="editorLoading || busy" @click="startSource(row.id)">选择此来源</el-button></template></el-table-column>
        </el-table>
        <el-pagination layout="prev,pager,next,total" :current-page="sourcePage" :page-size="10" :total="sourceTotal" @current-change="sourcePage = $event; loadSources()" />
      </el-tab-pane>
      <el-tab-pane label="已保存退货单" name="saved">
        <form class="return-search" @submit.prevent="savedPage = 1; loadSaved()">
          <el-input v-model="returnNumber" placeholder="输入退货单编号" clearable aria-label="退货单查询编号" />
          <el-input v-model="returnCustomer" placeholder="输入客户名称或编号" clearable aria-label="退货客户" />
          <el-button type="primary" native-type="submit" :loading="savedLoading">查询退货单</el-button>
          <el-button @click="loadSaved">刷新退货列表</el-button>
        </form>
        <el-alert v-if="savedError" :title="savedError" type="error" :closable="false"><el-button @click="loadSaved">重新查询退货单</el-button></el-alert>
        <el-table :data="savedRows" v-loading="savedLoading" border empty-text="尚无符合条件的退货单，可先从已审核销售单开草稿">
          <el-table-column prop="number" label="退货单编号" min-width="210" />
          <el-table-column prop="sourceNumber" label="来源销售单" min-width="200" />
          <el-table-column prop="customerName" label="客户" min-width="150" />
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
    <el-dialog v-model="editorVisible" :title="savedId ? '销售退货单详情' : '新建销售退货草稿'" width="1100px" top="4vh" :close-on-click-modal="false" :close-on-press-escape="!busy" :show-close="!busy">
      <div class="editor-scroll">
      <el-alert v-if="editorError" :title="editorError" type="error" :closable="false" show-icon><el-button v-if="savedId" :disabled="busy" @click="openReturn(savedId)">重新读取草稿</el-button></el-alert>
      <el-alert v-if="readOnly" title="当前单据已有核对、审核或关联状态，请按业务流程处理，不能直接修改。" type="info" :closable="false" />
      <p class="source-caption">来源：{{ sourceLabel }}　客户：{{ customerLabel }} <el-tag v-if="savedId">已保存</el-tag></p>
      <el-form label-position="top" :disabled="busy || readOnly" class="draft-fields">
        <el-form-item label="退货单编号" required><el-input v-model="form.number" maxlength="32" aria-label="退货单编号" /></el-form-item>
        <el-form-item label="退货日期" required><el-date-picker v-model="form.time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="选择退货日期" /></el-form-item>
        <el-form-item label="计划退款金额"><el-input v-model.number="form.money" type="number" min="0" step="0.0001" aria-label="计划退款金额" /></el-form-item>
        <el-form-item label="单据费用"><el-input v-model.number="form.cost" type="number" min="0" step="0.0001" aria-label="单据费用" /></el-form-item>
        <el-form-item :label="form.money > 0 ? '退款账户（必选）' : '退款账户（无退款可不选）'"><el-select v-model="form.account" filterable remote clearable :remote-method="searchAccounts" :loading="accountLoading" placeholder="按账户名称或编号搜索" aria-label="退款账户"><el-option v-for="account in accounts" :key="account.id" :value="account.id" :label="`${account.name} ${account.number || ''}`" /></el-select></el-form-item>
      </el-form>
      <el-alert v-if="accountError" :title="accountError" type="error" :closable="false" />
      <el-table :data="rows" border max-height="360">
        <el-table-column label="退货" width="70"><template #default="{ row }"><el-checkbox v-model="row.selected" :disabled="busy || readOnly" :aria-label="`退货 ${row.goodsName}`" /></template></el-table-column>
        <el-table-column prop="goodsName" label="来源商品" min-width="150" />
        <el-table-column prop="warehouseName" label="原出库仓库" min-width="150" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column label="退货数量" width="180"><template #default="{ row }"><el-input v-model.number="row.quantity" type="number" min="0" step="0.0001" :disabled="busy || readOnly" :aria-label="`退货数量 ${row.goodsName}`" /></template></el-table-column>
        <el-table-column prop="available" label="读取时可退" width="110" />
        <el-table-column prop="price" label="来源单价" width="110" />
        <el-table-column label="预计含税金额" width="140"><template #default="{ row }">{{ estimate(row).toFixed(4) }}</template></el-table-column>
      </el-table>
      <p>选中明细预计含税合计：{{ estimatedTotal }}。保存后以重新读取的金额为准。</p>
      <p class="guide">商品、仓库、单位和价格来自原销售单。取消勾选可不退该行；保存时会重新检查可退数量并计算金额。</p>
      <el-form label-position="top" :disabled="busy || readOnly"><el-form-item label="退货备注"><el-input v-model="form.data" type="textarea" maxlength="256" show-word-limit /></el-form-item></el-form>
      </div>
      <template #footer><el-button :disabled="busy" @click="editorVisible = false">关闭</el-button><el-button type="primary" :loading="busy" :disabled="readOnly || (savedId !== '' && version === '')" @click="save">{{ savedId ? '保存草稿修改' : '保存退货草稿' }}</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { saleOrderApi } from '@/apis/sales/order'
import { returnDraftApi } from '@/apis/sales/returnDraft'
import type { ReturnDraftInput } from '@/apis/sales/returnDraft'
import { extractApiErrorMessage } from '@/utils/formValidation'

const route = useRoute()
const router = useRouter()
const tab = ref(route.name === 'SalesReturnReport' || typeof route.query.draft === 'string' ? 'saved' : 'source')
const sourceNumber = ref(''), sourceCustomer = ref(''), sourcePage = ref(1), sourceTotal = ref(0), sources = ref<Record<string, any>[]>([]), sourceLoading = ref(false), sourceError = ref('')
const returnNumber = ref(''), returnCustomer = ref(''), savedPage = ref(1), savedTotal = ref(0), savedRows = ref<Record<string, any>[]>([]), savedLoading = ref(false), savedError = ref('')
const entryError = ref(''), editorError = ref(''), editorVisible = ref(false), editorLoading = ref(false), busy = ref(false)
const savedId = ref(''), version = ref(''), sourceId = ref(''), sourceVersion = ref(''), sourceLabel = ref(''), customerLabel = ref(''), readOnly = ref(false)
const rows = ref<Record<string, any>[]>([]), accounts = ref<Record<string, any>[]>([]), accountLoading = ref(false), accountError = ref('')
const form = reactive({ number: '', time: '', money: 0, cost: 0, account: '', data: '' })
let sourceSequence = 0, savedSequence = 0, editorSequence = 0, accountSequence = 0
function estimate(row: Record<string, any>) { const quantity = Number(row.quantity), original = Number(row.nums); return Number.isFinite(quantity) && original > 0 ? Math.round(Number(row.tpt || 0) * quantity / original * 10000) / 10000 : 0 }
const estimatedTotal = computed(() => rows.value.filter(row => row.selected).reduce((total, row) => total + estimate(row), 0).toFixed(4))
async function loadSources() {
  const sequence = ++sourceSequence; sourceLoading.value = true; sourceError.value = ''
  try { const result = await saleOrderApi.getSaleList({ pageIndex: sourcePage.value, pageSize: 10, number: sourceNumber.value.trim() || undefined, customer: sourceCustomer.value.trim() || undefined, examine: 1 }); if (sequence !== sourceSequence) return; if (result.code !== 10000 || !Array.isArray(result.data?.rows)) throw new Error(result.message || '销售单查询失败'); sources.value = result.data.rows; sourceTotal.value = Number(result.data.total) }
  catch (error) { if (sequence === sourceSequence) { sources.value = []; sourceTotal.value = 0; sourceError.value = extractApiErrorMessage(error) } }
  finally { if (sequence === sourceSequence) sourceLoading.value = false }
}
async function loadSaved() {
  const sequence = ++savedSequence; savedLoading.value = true; savedError.value = ''
  try { const result = await returnDraftApi.list({ pageIndex: savedPage.value, pageSize: 10, id: returnNumber.value.trim() || undefined, customer: returnCustomer.value.trim() || undefined }); if (sequence !== savedSequence) return; savedRows.value = result.rows || []; savedTotal.value = Number(result.total) }
  catch (error) { if (sequence === savedSequence) { savedRows.value = []; savedTotal.value = 0; savedError.value = extractApiErrorMessage(error) } }
  finally { if (sequence === savedSequence) savedLoading.value = false }
}
function today() { const date = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()); return date + ' 00:00:00' }
async function startSource(id: string, expectedVersion?: string) {
  accountSequence++; accountLoading.value = false
  const sequence = ++editorSequence; editorLoading.value = true; entryError.value = ''
  try {
    const document = await saleOrderApi.getDocument(id), result = await saleOrderApi.getGenerateReturnData(id)
    if (sequence !== editorSequence) return
    if (document.code !== 10000 || result.code !== 10000 || !result.data || !document.data) throw new Error(result.message || document.message || '来源销售单读取失败')
    const preview = result.data
    if (preview.source !== id || preview.sourceVersion !== document.data.version || (expectedVersion && expectedVersion !== preview.sourceVersion)) throw new Error('来源销售单已变化，请重新查询并核对后选择')
    savedId.value = ''; version.value = ''; sourceId.value = id; sourceVersion.value = preview.sourceVersion; sourceLabel.value = preview.sourceNumber; customerLabel.value = document.data.header.customerName || preview.customer
    rows.value = preview.items.map(item => ({ ...item, selected: true, quantity: item.available }))
    Object.assign(form, { number: 'XSTH' + Date.now(), time: today(), money: 0, cost: 0, account: '', data: '' })
    accounts.value = []; editorError.value = ''; accountError.value = ''; readOnly.value = false; editorVisible.value = true; void searchAccounts('')
  } catch (error) { if (sequence === editorSequence) entryError.value = extractApiErrorMessage(error) }
  finally { if (sequence === editorSequence) editorLoading.value = false }
}
async function openReturn(id: string) {
  accountSequence++; accountLoading.value = false
  const sequence = ++editorSequence; editorLoading.value = true; entryError.value = ''
  try {
    const document = await returnDraftApi.document(id); if (sequence !== editorSequence) return
    const head = document.header
    savedId.value = id; version.value = document.version; sourceId.value = String(head.source); sourceVersion.value = document.sourceVersion; sourceLabel.value = head.sourceNumber || String(head.source); customerLabel.value = head.customerName || String(head.customer)
    rows.value = document.items.map(item => ({ ...item, selected: true, quantity: Number(item.nums), available: '保存时复核' }))
    Object.assign(form, { number: head.number, time: head.timeText, money: Number(head.money), cost: Number(head.cost || 0), account: head.account || '', data: head.data || '' })
    accounts.value = head.account ? [{ id: String(head.account), name: head.accountName || String(head.account) }] : []
    readOnly.value = Number(head.examine) !== 0 || Number(head.check) !== 0 || Number(head.nucleus) !== 0
    editorError.value = ''; accountError.value = ''; editorVisible.value = true; void searchAccounts('')
  } catch (error) { if (sequence === editorSequence) { const message = extractApiErrorMessage(error); if (editorVisible.value) editorError.value = message; else entryError.value = message } }
  finally { if (sequence === editorSequence) editorLoading.value = false }
}
async function searchAccounts(keyword: string) {
  if (!sourceId.value) return
  const sequence = ++accountSequence; accountLoading.value = true; accountError.value = ''
  try { const result = await returnDraftApi.accounts(sourceId.value, keyword, !!savedId.value); if (sequence === accountSequence) { const current = accounts.value.filter(item => item.id === form.account); accounts.value = [...current, ...result.filter(item => !current.some(existing => existing.id === item.id))] } }
  catch (error) { if (sequence === accountSequence) accountError.value = extractApiErrorMessage(error) }
  finally { if (sequence === accountSequence) accountLoading.value = false }
}
async function save() {
  if (busy.value || readOnly.value || (savedId.value && !version.value)) return
  editorError.value = ''
  const selected = rows.value.filter(row => row.selected)
  if (!form.number.trim() || !form.time || !selected.length || selected.some(row => !Number.isFinite(Number(row.quantity)) || Number(row.quantity) <= 0)) { editorError.value = '请填写编号、退货日期，并勾选至少一条数量大于零的明细'; return }
  if (form.money > 0 && !form.account) { editorError.value = '填写计划退款金额时请选择退款账户'; return }
  const input: ReturnDraftInput = { id: savedId.value || undefined, version: version.value || undefined, source: sourceId.value, sourceVersion: sourceVersion.value, number: form.number.trim(), time: form.time, money: Number(form.money || 0), cost: Number(form.cost || 0), account: form.account, data: form.data, salesReturnOrderInfos: selected.map(row => ({ id: savedId.value ? row.id : undefined, source: row.source, nums: Number(row.quantity), serial: row.serial || '[]', data: row.data || '' })) }
  busy.value = true
  try {
    const id = await returnDraftApi.save(input); savedId.value = id; version.value = ''
    returnNumber.value = input.number; savedPage.value = 1; tab.value = 'saved'
    await openReturn(id)
    if (!version.value) editorError.value = '草稿已保存，详情读取失败，请重新读取草稿；不要重复新增'
    else ElMessage.success('退货草稿已保存，未入库或退款')
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
