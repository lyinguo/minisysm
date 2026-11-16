<template>
  <el-dialog v-model="visible" title="导入完整付款草稿" width="min(1100px, 95vw)" :before-close="beforeClose" :close-on-click-modal="false" :close-on-press-escape="!busy" destroy-on-close>
    <el-alert title="① 下载模板并填写　② 上传后预览核对　③ 确认整批保存草稿。此处不扣款，保存后打开付款单核对原采购和退货抵扣，再审核入账。" type="info" :closable="false" show-icon />
    <p>同一付款单编号的多行账户明细会合并为一张单，供应商、日期和单据备注须一致。请填写供应商和账户的<strong>业务编号</strong>，可到基础资料中查看；模板内另有“填写说明”。</p>
    <div class="import-actions">
      <el-button :disabled="busy" @click="downloadTemplate">下载付款模板.xlsx</el-button>
      <label class="file-picker">选择已填写的模板<input aria-label="选择付款模板文件" type="file" accept=".xlsx,.xls" :disabled="busy" @change="readFile" /></label>
      <span>{{ filename || '尚未选择文件，最大1MiB' }}</span>
      <el-button v-if="rows.length" :disabled="busy" @click="preview">重新预览核对</el-button>
    </div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-if="plan">
      <div class="import-summary"><strong>{{ plan.documentCount }} 张付款草稿</strong><span>{{ plan.lineCount }} 条账户明细</span><span>计划付款合计 {{ plan.cash }}</span></div>
      <el-table :data="rows" border max-height="420" empty-text="模板尚无数据">
        <el-table-column prop="number" label="付款单编号" min-width="180" />
        <el-table-column prop="date" label="付款日期" width="120" />
        <el-table-column prop="supplierNumber" label="供应商编号" min-width="140" />
        <el-table-column prop="accountNumber" label="结算账户编号" min-width="140" />
        <el-table-column prop="money" label="付款金额" width="120" />
        <el-table-column prop="settle" label="结算号" min-width="120" />
        <el-table-column prop="remark" label="单据备注" min-width="140" />
        <el-table-column prop="lineRemark" label="明细备注" min-width="140" />
      </el-table>
      <p>所有数据已由服务端校验。确认时会再次核对；任一单据失败，整批不保存。</p>
    </template>
    <template #footer>
      <el-button :disabled="busy" @click="visible = false">关闭</el-button>
      <el-button type="primary" :loading="busy" :disabled="!plan || uncertain" @click="commit">确认导入 {{ plan?.documentCount || 0 }} 张草稿</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, shallowRef, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as XLSX from 'xlsx'
import { paymentTemplateBook, parsePaymentTemplate } from '@/apis/finance/paymentTemplate'
import { paymentWorkflow, type PaymentImportRow, type PaymentImportPlan } from '@/apis/finance/paymentWorkflow'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'

const visible = defineModel<boolean>({ default: false })
const emit = defineEmits<{ saved: [ids: string[]] }>()
const rows = shallowRef<PaymentImportRow[]>([])
const plan = shallowRef<PaymentImportPlan>()
const filename = ref(''), error = ref(''), busy = ref(false), uncertain = ref(false)
watch(visible, value => { if (value) { rows.value = []; plan.value = undefined; filename.value = ''; error.value = ''; uncertain.value = false } })
function beforeClose(done: () => void) { if (!busy.value) done() }
function downloadTemplate() { XLSX.writeFile(paymentTemplateBook(), '付款草稿导入模板.xlsx') }
async function preview() {
  if (busy.value || !rows.value.length) return
  busy.value = true; error.value = ''; plan.value = undefined
  try { plan.value = await paymentWorkflow.importPreview(rows.value); uncertain.value = false }
  catch (failure) { error.value = extractErrorMessage(failure) }
  finally { busy.value = false }
}
async function readFile(event: Event) {
  const input = event.target as HTMLInputElement, file = input.files?.[0]
  input.value = ''
  if (!file || busy.value) return
  plan.value = undefined; rows.value = []; error.value = ''; filename.value = file.name; uncertain.value = false
  busy.value = true
  try {
    if (!file.size || file.size > 1024 * 1024) throw new Error('请选择非空模板文件，最大1MiB')
    rows.value = parsePaymentTemplate(await file.arrayBuffer())
  } catch (failure) { error.value = extractErrorMessage(failure) }
  finally { busy.value = false }
  if (rows.value.length) await preview()
}
async function commit() {
  if (busy.value || !plan.value || uncertain.value) return
  const reviewed = plan.value, snapshot = JSON.stringify(rows.value)
  try { await ElMessageBox.confirm(`将保存${reviewed.documentCount}张草稿、${reviewed.lineCount}条账户明细，计划付款合计${reviewed.cash}。不会自动扣款。`, '确认导入完整付款草稿', { type: 'warning' }) } catch { return }
  if (busy.value || plan.value !== reviewed || JSON.stringify(rows.value) !== snapshot) { error.value = '模板或预览已变化，请重新预览核对'; return }
  busy.value = true; error.value = ''
  try {
    const result = await paymentWorkflow.importSave(JSON.parse(snapshot), reviewed.version)
    plan.value = undefined; visible.value = false; emit('saved', result.ids)
    ElMessage.success(`已保存${result.documentCount}张真实付款草稿，请打开单据核对结算方案`)
  } catch (failure) { uncertain.value = true; error.value = extractErrorMessage(failure) + '；本次导入未确认，请先按单据编号查询结果，再重新预览核对，避免重复导入。' }
  finally { busy.value = false }
}
</script>

<style scoped>
.import-actions,.import-summary{display:flex;flex-wrap:wrap;align-items:center;gap:16px;margin:18px 0}.import-summary{padding:16px;background:#f0f7ff;border-radius:8px}.file-picker{display:flex;align-items:center;gap:8px}p{line-height:1.7;color:#526176}
</style>
