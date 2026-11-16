<template>
  <section class="payment-workspace">
    <header class="workspace-heading"><div><h2>供应商付款</h2><p>保存草稿 → 核对采购款及退货抵扣 → 审核付款。保存不会扣款，审核后同步资金流水和原单核销。</p></div><el-button type="primary" :disabled="busy" @click="newDraft">新建付款草稿</el-button></header>
    <el-alert v-if="listError" :title="listError" type="error" :closable="false" show-icon />
    <form class="toolbar" @submit.prevent="page = 1; loadList()">
      <el-input v-model="filters.number" placeholder="付款单编号" aria-label="付款查询编号" clearable />
      <el-input v-model="filters.supplier" placeholder="供应商名称或编号" clearable />
      <el-select v-model="filters.examine" placeholder="审核状态" clearable><el-option label="草稿" value="0" /><el-option label="已审核" value="1" /></el-select>
      <el-button native-type="submit" :loading="loading">查询</el-button><el-button :disabled="loading" @click="loadList">刷新</el-button>
      <el-button :disabled="busy" @click="importVisible = true">模板导入</el-button>
      <el-button :disabled="busy" @click="exportFile('simple')">导出汇总</el-button><el-button :disabled="busy" @click="exportFile('detail')">导出账户明细</el-button>
    </form>
    <el-table :data="rows" row-key="id" v-loading="loading" border empty-text="没有符合条件的付款单，可新建草稿或导入完整模板">
      <el-table-column prop="number" label="付款单编号" min-width="190" /><el-table-column prop="supplierName" label="供应商" min-width="170" /><el-table-column prop="timeText" label="付款日期" width="120" /><el-table-column prop="total" label="实际付款金额" width="140" />
      <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="row.examine === 1 ? 'success' : 'info'">{{ row.examine === 1 ? (row.nucleus === 2 ? '已审核 · 已核销' : row.nucleus === 1 ? '已审核 · 部分核销' : '已审核 · 待核销') : '待核对草稿' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="140" fixed="right"><template #default="{ row }"><el-button link type="primary" :disabled="busy" @click="openDocument(row.id)">查看 / 处理</el-button></template></el-table-column>
    </el-table>
    <el-pagination layout="prev,pager,next,total" :current-page="page" :page-size="10" :total="total" @current-change="page = $event; loadList()" />

    <el-dialog v-model="editorVisible" :title="id ? '付款单详情' : '新建付款草稿'" width="min(1200px, 96vw)" :before-close="closeEditor" :close-on-click-modal="false" :close-on-press-escape="!busy" destroy-on-close>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
      <el-alert v-if="approved" title="已审核单据只读。反审核会按本次入账凭据撤销资金及核销；有关联费用、发票时请先处理。缺少入账凭据的历史单据需核对处理，不能自动反冲。" type="success" :closable="false" />
      <el-alert v-else title="请填写本次实际支付的账户和金额。退货抵扣在下一步单独核对，不作为账户付款金额填写。" type="info" :closable="false" />
      <el-form label-position="top" :disabled="busy || approved || rereadRequired" class="payment-form">
        <el-form-item label="付款单编号"><el-input v-model="form.number" aria-label="付款单编号" maxlength="32" /></el-form-item>
        <el-form-item label="付款日期"><el-date-picker v-model="form.time" type="date" value-format="YYYY-MM-DD" placeholder="选择付款日期" /></el-form-item>
        <el-form-item label="供应商"><el-select v-model="form.supplier" filterable remote :remote-method="searchSuppliers" :loading="supplierLoading" placeholder="输入供应商名称或编号搜索" @visible-change="$event && searchSuppliers('')"><el-option v-for="option in supplierOptions" :key="option.id" :value="option.id" :label="option.number ? `${option.name}（${option.number}）` : option.name" /></el-select></el-form-item>
        <el-form-item label="单据备注"><el-input v-model="form.data" aria-label="付款备注" maxlength="256" /></el-form-item>
      </el-form>
      <p v-if="optionHint" class="help">{{ optionHint }}</p>
      <div class="section-heading"><h3>本次实际付款账户</h3><el-button v-if="!approved" :disabled="busy || rereadRequired" @click="form.details.push(blankLine())">添加账户明细</el-button></div>
      <el-table :data="form.details" border>
        <el-table-column label="结算账户" min-width="260"><template #default="{ row }"><el-select v-model="row.account" :disabled="busy || approved || rereadRequired" filterable remote :remote-method="searchAccounts" :loading="accountLoading" placeholder="输入账户名称或编号搜索" @visible-change="$event && searchAccounts('')"><el-option v-for="option in accountOptions" :key="option.id" :value="option.id" :label="option.number ? `${option.name}（${option.number}）` : option.name" /></el-select></template></el-table-column>
        <el-table-column label="付款金额" width="190"><template #default="{ row }"><el-input-number v-model="row.money" :min="0.0001" :max="99999999.9999" :precision="4" :controls="false" :disabled="busy || approved || rereadRequired" /></template></el-table-column>
        <el-table-column label="结算号" min-width="140"><template #default="{ row }"><el-input v-model="row.settle" maxlength="256" :disabled="busy || approved || rereadRequired" /></template></el-table-column>
        <el-table-column label="明细备注" min-width="150"><template #default="{ row }"><el-input v-model="row.data1" maxlength="256" :disabled="busy || approved || rereadRequired" /></template></el-table-column>
        <el-table-column v-if="!approved" label="操作" width="80"><template #default="{ $index }"><el-button link type="danger" :disabled="busy || rereadRequired || form.details.length < 2" @click="form.details.splice($index, 1)">移除</el-button></template></el-table-column>
      </el-table>
      <p class="amount">实际付款合计：{{ cash.toFixed(4) }}</p>
      <template v-if="plan && !approved">
        <div class="section-heading"><h3>核对原采购款与退货抵扣</h3><span>待付采购 {{ plan.invoiceTotal }} − 可用退货抵扣 {{ plan.creditTotal }} = 净应付 {{ plan.payableNet }}</span></div>
        <p>系统按先旧后新建议分配。可调整每张原单的本次金额；采购核销减退货抵扣必须等于实际付款。结清净应付时应同时处理全部剩余退货抵扣。</p>
        <el-table :data="allocationRows" border>
          <el-table-column label="原单类型" width="130"><template #default="{ row }">{{ row.type === 'buy' ? '采购单' : '采购退货单' }}</template></el-table-column>
          <el-table-column label="原单编号" min-width="190"><template #default="{ row }"><el-button link type="primary" @click="viewOriginal(row)">{{ row.number }}</el-button></template></el-table-column>
          <el-table-column prop="remaining" label="剩余可核销 / 抵扣" width="170" />
          <el-table-column label="本次核销 / 抵扣" min-width="190"><template #default="{ row }"><el-input-number v-model="row.chosen" :min="0" :max="Number(row.remaining)" :precision="4" :controls="false" :disabled="busy" /></template></el-table-column>
        </el-table>
        <p class="amount">采购核销减退货抵扣：{{ allocationNet.toFixed(4) }}；实际付款：{{ cash.toFixed(4) }}</p>
      </template>
      <template v-if="document?.allocations.length"><h3>已入账原单核销记录</h3><el-table :data="document.allocations" border><el-table-column label="原单编号" min-width="210"><template #default="{ row }"><el-button link @click="viewOriginal({ type: row.type, number: row.sourceNumber, id: row.source })">{{ row.sourceNumber }}</el-button></template></el-table-column><el-table-column label="来源类型"><template #default="{ row }">{{ row.type === 'buy' ? '采购单' : row.type === 'bre' ? '采购退货单' : '历史关联单据' }}</template></el-table-column><el-table-column prop="money" label="核销金额（负数为退货抵扣）" min-width="220" /></el-table></template>
      <template v-if="document?.expenses?.length"><h3>关联费用（需先处理后才能反审核）</h3><el-table :data="document.expenses" border><el-table-column prop="id" label="费用记录ID" min-width="230" /><el-table-column prop="expenseName" label="费用类别" /><el-table-column prop="money" label="金额" /><el-table-column prop="data" label="备注" /></el-table></template>
      <template v-if="document?.invoices?.length"><h3>关联发票</h3><el-table :data="document.invoices" border><el-table-column prop="number" label="发票号码" /><el-table-column prop="title" label="发票抬头" /><el-table-column prop="money" label="金额" /></el-table></template>
      <template #footer>
        <el-button :disabled="busy" @click="closeEditor(() => editorVisible = false)">关闭</el-button>
        <el-button v-if="id" :disabled="busy" @click="reloadDocument">重新读取</el-button>
        <el-button v-if="!approved" type="primary" :loading="busy" :disabled="rereadRequired" @click="save">{{ id ? '保存草稿修改' : '保存付款草稿' }}</el-button>
        <el-button v-if="id && !approved" :disabled="busy || rereadRequired" @click="previewSettlement">核对结算方案</el-button>
        <el-button v-if="plan && !approved" type="success" :disabled="busy || rereadRequired" @click="settle(1)">确认付款并核销</el-button>
        <el-button v-if="approved" type="warning" :disabled="busy || rereadRequired" @click="settle(0)">反审核并撤销本次付款</el-button>
        <el-button v-if="id && !approved" type="danger" :disabled="busy || rereadRequired" @click="remove">删除草稿</el-button>
      </template>
    </el-dialog>
    <PaymentImportDialog v-model="importVisible" @saved="importSaved" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteUpdate, onBeforeRouteLeave, type RouteLocationNormalized } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { paymentWorkflow as api, type PaymentDocument, type PaymentPlan, type PaymentAllocation } from '@/apis/finance/paymentWorkflow'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import { downloadExportBlob } from '@/utils/reportMappers'
import PaymentImportDialog from './PaymentImportDialog.vue'

type Line = { id?: string; pid?: string; account: string; money: number; settle: string; data1: string }
type Option = { id: string; name: string; number: string }
type AllocationRow = PaymentAllocation & { chosen: number }
const route = useRoute(), router = useRouter()
const rows = ref<Record<string, any>[]>([]), total = ref(0), page = ref(1), loading = ref(false), listError = ref('')
const filters = reactive({ number: '', supplier: '', examine: '' })
const busy = ref(false), editorVisible = ref(false), importVisible = ref(false), error = ref(''), id = ref(''), rereadRequired = ref(false)
const document = shallowRef<PaymentDocument>(), plan = shallowRef<PaymentPlan>(), allocationRows = ref<AllocationRow[]>([])
const form = reactive({ number: '', supplier: '', time: '', data: '', details: [] as Line[] })
const supplierOptions = ref<Option[]>([]), accountOptions = ref<Option[]>([]), supplierLoading = ref(false), accountLoading = ref(false), optionHint = ref('')
let clean = '', requestNumber = 0, supplierRequest = 0, accountRequest = 0
const snapshot = () => JSON.stringify(form)
const dirty = computed(() => snapshot() !== clean)
const approved = computed(() => document.value?.header.examine === 1)
const cash = computed(() => form.details.reduce((sum, line) => sum + Number(line.money || 0), 0))
const allocationNet = computed(() => allocationRows.value.reduce((sum, row) => sum + (row.type === 'buy' ? 1 : -1) * Number(row.chosen || 0), 0))
function blankLine(): Line { return { account: '', money: 1, settle: '', data1: '' } }
function today() { const now = new Date();return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}` }
async function loadList() {
  const current = ++requestNumber;loading.value = true;listError.value = ''
  try { const result = await api.list({ ...filters, pageIndex: page.value, pageSize: 10 });if (current === requestNumber) { rows.value = result.rows;total.value = result.total } }
  catch (failure) { if (current === requestNumber) listError.value = extractErrorMessage(failure) }
  finally { if (current === requestNumber) loading.value = false }
}
async function newDraft() {
  if (busy.value) return
  if(typeof route.query.payment === 'string') { const cancelled = await router.replace({ path: route.path, query: { ...route.query, payment: undefined } });if(cancelled)return }
  supplierRequest++;accountRequest++
  id.value = '';document.value = undefined;plan.value = undefined;allocationRows.value = [];rereadRequired.value = false;error.value = '';optionHint.value = ''
  Object.assign(form, { number: 'FK' + Date.now() + Math.random().toString(16).slice(2, 8), time: today(), supplier: '', data: '', details: [blankLine()] });clean = snapshot();supplierOptions.value = [];accountOptions.value = [];editorVisible.value = true
}
async function openDocument(identifier: string) {
  if (busy.value) return
  supplierRequest++;accountRequest++;optionHint.value = ''
  busy.value = true;error.value = '';plan.value = undefined
  try {
    const result = await api.document(identifier);id.value = identifier;document.value = result
    Object.assign(form, { number: result.header.number, supplier: result.header.supplier, time: result.header.timeText, data: result.header.data || '', details: result.items.map(row => ({ id: row.id, pid: row.pid, account: row.account, money: Number(row.money), settle: row.settle || '', data1: row.data || '' })) })
    supplierOptions.value = [{ id: result.header.supplier, name: result.header.supplierName, number: '' }]
    accountOptions.value = result.items.map(row => ({ id: row.account, name: row.accountName, number: row.accountNumber }))
    clean = snapshot();rereadRequired.value = false;editorVisible.value = true
    if(route.query.payment !== identifier) await router.replace({ path: route.path, query: { ...route.query, payment: identifier } })
  } catch (failure) { error.value = extractErrorMessage(failure);ElMessage.error(error.value) }
  finally { busy.value = false }
}
async function closeEditor(done: () => void) { if (busy.value) return;if (dirty.value) { try { await ElMessageBox.confirm('有未保存的修改，关闭将放弃这些输入。', '关闭付款单', { type: 'warning' }) } catch { return } } clean = snapshot();done();if(typeof route.query.payment === 'string') await router.replace({ path: route.path, query: { ...route.query, payment: undefined } }) }
async function reloadDocument() { if (busy.value || !id.value) return;if (dirty.value) { try { await ElMessageBox.confirm('重新读取将放弃未保存输入，请确认。', '读取最新付款单') } catch { return } } await openDocument(id.value) }
async function searchOptions(kind: 'supplier' | 'account', keyword: string) {
  const current = kind === 'supplier' ? ++supplierRequest : ++accountRequest
  const active = kind === 'supplier' ? supplierLoading : accountLoading;active.value = true
  try { const result = await api.options(kind, keyword, id.value || undefined);if (current !== (kind === 'supplier' ? supplierRequest : accountRequest)) return;const target = kind === 'supplier' ? supplierOptions : accountOptions;target.value = [...result.rows, ...target.value.filter(old => (kind === 'supplier' ? form.supplier === old.id : form.details.some(row => row.account === old.id)) && !result.rows.some(row => row.id === old.id))];optionHint.value = result.hasMore ? '符合条件的选项超过50条，请输入更完整的名称或编号继续搜索。' : '' }
  catch (failure) { error.value = extractErrorMessage(failure) }
  finally { if (current === (kind === 'supplier' ? supplierRequest : accountRequest)) active.value = false }
}
const searchSuppliers = (keyword: string) => searchOptions('supplier', keyword)
const searchAccounts = (keyword: string) => searchOptions('account', keyword)
async function save() {
  if (busy.value || approved.value || rereadRequired.value) return
  if (!form.number.trim() || !form.time || !form.supplier || !form.details.length || form.details.some(row => !row.account || !Number.isFinite(row.money) || row.money <= 0)) { error.value = '请填写编号、日期、供应商，以及每条实际付款账户和正数金额';return }
  busy.value = true;error.value = '';plan.value = undefined
  let saved = false
  try { const body = { number: form.number, time: form.time, supplier: form.supplier, data: form.data, ...(id.value ? { version: document.value?.version, details: form.details } : { file: '[]', infoList: form.details }) };const identifier = await api.save(id.value || undefined, body);id.value = identifier;rereadRequired.value = true;saved = true;clean = snapshot();await router.replace({ path: route.path, query: { payment: identifier } });ElMessage.success('付款草稿已保存，尚未扣款') }
  catch (failure) { error.value = extractErrorMessage(failure) }
  finally { busy.value = false }
  if (saved) { await openDocument(id.value);await loadList() }
}
function needsSaved() { if (dirty.value) { error.value = '请先保存未提交的修改，再核对或处理付款';return true }return false }
async function previewSettlement() {
  if (busy.value || !id.value || needsSaved()) return
  busy.value = true;error.value = '';plan.value = undefined
  try { const result = await api.preview(id.value);if (result.version !== document.value?.version) throw new Error('付款单已变化，请重新读取核对，本次未付款');plan.value = result;allocationRows.value = result.documents.map(row => ({ ...row, chosen: Math.abs(Number(result.allocations.find(line => line.id === row.id && line.type === row.type)?.money || 0)) })) }
  catch (failure) { error.value = extractErrorMessage(failure) }
  finally { busy.value = false }
}
async function settle(target: 0 | 1) {
  if (busy.value || !id.value || !document.value || needsSaved()) return
  if (target && (!plan.value || Math.abs(allocationNet.value - cash.value) > 0.000001)) { error.value = '请核对结算方案，采购核销减退货抵扣必须等于实际付款';return }
  const reviewed = document.value.version, identifier = id.value, input = snapshot(), selected = JSON.stringify(allocationRows.value)
  try { await ElMessageBox.confirm(target ? `将实际支付${cash.value}，并同步核销原采购及退货抵扣。确认账户和原单无误后继续。` : '将撤销本次付款及原单核销，恢复账户资金和供应商应付。有关联费用、发票等时需先处理。', target ? '确认付款入账' : '确认反审核付款', { type: 'warning' }) } catch { return }
  if (busy.value || id.value !== identifier || document.value?.version !== reviewed || snapshot() !== input || JSON.stringify(allocationRows.value) !== selected) { error.value = '付款内容或结算方案已变化，请重新核对';return }
  busy.value = true;error.value = '';let completed = false
  try { const allocations = target ? JSON.parse(selected).filter((row: AllocationRow) => row.chosen > 0).map((row: AllocationRow) => ({ ...row, money: row.type === 'buy' ? row.chosen : -row.chosen })) : undefined;await api.settle(identifier, target, reviewed, allocations);rereadRequired.value = true;plan.value = undefined;completed = true;ElMessage.success(target ? '实际付款及原单核销已完成' : '本次付款及核销已撤销') }
  catch (failure) { error.value = extractErrorMessage(failure) }
  finally { busy.value = false }
  if (completed) { await openDocument(identifier);await loadList() }
}
async function remove() {
  if (busy.value || !id.value || !document.value || needsSaved()) return
  const identifier = id.value, reviewed = document.value.version
  try { await ElMessageBox.confirm('将删除这张未入账付款草稿，保留操作历史。', '删除付款草稿', { type: 'warning' }) } catch { return }
  if (busy.value || id.value !== identifier || document.value?.version !== reviewed || dirty.value) return
  busy.value = true;error.value = ''
  try { await api.remove(identifier, reviewed);editorVisible.value = false;id.value = '';document.value = undefined;await router.replace({ path: route.path, query: {} });ElMessage.success('付款草稿已删除');await loadList() }
  catch (failure) { error.value = extractErrorMessage(failure) }
  finally { busy.value = false }
}
async function exportFile(kind: 'simple' | 'detail') { try { downloadExportBlob(await api.export(kind, { ...filters }), `付款单-${kind}.xlsx`) } catch (failure) { listError.value = extractErrorMessage(failure) } }
function viewOriginal(row: { type: string; number: string; id: string }) { const target = row.type === 'buy' ? { name: 'PurchaseOrderReport', query: { number: row.number } } : { name: 'PurchaseReturnReport', query: { draft: row.id } };window.open(router.resolve(target).href, '_blank', 'noopener') }
async function importSaved(ids: string[]) { await loadList();if (ids.length === 1) await openDocument(ids[0]);else { filters.number = '';await loadList() } }
async function allowNavigation(to: RouteLocationNormalized) {
  if (to.path === route.path && (to.query.payment || '') === id.value) return true
  if (busy.value) return false
  if (editorVisible.value && dirty.value) { try { await ElMessageBox.confirm('页面将切换，有未保存的付款输入。确认放弃这些修改？', '离开付款单', { type: 'warning' }) } catch { return false } }
  return true
}
onBeforeRouteUpdate(allowNavigation)
onBeforeRouteLeave(allowNavigation)
watch(() => [route.path, route.query.payment] as const, ([, next]) => {
  if (typeof next === 'string' && next !== id.value) void openDocument(next)
  else if (typeof next !== 'string') { editorVisible.value = false;plan.value = undefined }
})
onMounted(() => { void loadList();if (typeof route.query.payment === 'string') void openDocument(route.query.payment) })
</script>

<style scoped>
.payment-workspace{padding:24px;display:grid;gap:18px;background:#fff;border-radius:12px}.workspace-heading,.toolbar,.section-heading{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:14px}.workspace-heading h2{margin:0 0 8px}.workspace-heading p,p{line-height:1.7;color:#526176}.toolbar{justify-content:flex-start}.toolbar>.el-input{width:200px}.toolbar>.el-select{width:140px}.payment-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 20px;margin-top:18px}.payment-form .el-select,.payment-form .el-date-editor{width:100%}.section-heading{margin-top:18px}.amount{text-align:right;font-weight:600;color:#24548d}.help{color:#b76b00}@media(max-width:700px){.payment-workspace{padding:12px}.payment-form{grid-template-columns:1fr}}
</style>
