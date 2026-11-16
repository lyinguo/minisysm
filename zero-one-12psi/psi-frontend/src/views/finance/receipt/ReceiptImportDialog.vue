<template>
  <el-dialog v-model="visible" title="导入客户收款草稿" width="min(1120px, 96vw)" :before-close="beforeClose" :close-on-click-modal="false" :close-on-press-escape="!busy" destroy-on-close>
    <el-alert title="① 下载模板　② 填写后上传核对　③ 确认整批保存草稿。保存不会增加账户余额，请再打开收款单核对销售及退货后确认收款。" type="info" :closable="false" show-icon />
    <p>每行填写一个收款账户和金额；同一收款单编号的明细会合并，其客户、时间和单据备注必须一致。<strong>客户编号</strong>在客户管理查看，<strong>结算账户编号</strong>在账户管理查看。模板另有“填写说明”，不要填写内部 ID。</p>
    <div class="actions"><el-button :disabled="busy" @click="downloadTemplate">下载收款模板.xlsx</el-button><label>选择已填写的模板 <input aria-label="选择收款模板文件" type="file" accept=".xlsx,.xls" :disabled="busy" @change="selectFile" /></label><span>{{ file?.name || '尚未选择文件，最大5MiB' }}</span><el-button v-if="file" :disabled="busy" @click="preview">重新预览核对</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-if="plan">
      <div class="summary"><strong>{{ plan.documentCount }} 张收款草稿</strong><span>{{ plan.lineCount }} 条账户明细</span><span>计划收款合计 {{ plan.cash }}</span></div>
      <el-table :data="previewRows" border max-height="420">
        <el-table-column prop="number" label="收款单编号" min-width="180" /><el-table-column prop="date" label="收款时间" width="180" />
        <el-table-column label="客户" min-width="180"><template #default="{ row }">{{ row.customer || '未命名客户' }}<small>{{ row.customerNumber }}</small></template></el-table-column>
        <el-table-column label="结算账户" min-width="180"><template #default="{ row }">{{ row.account || '未命名账户' }}<small>{{ row.accountNumber }}</small></template></el-table-column>
        <el-table-column prop="money" label="收款金额" width="140" />
      </el-table>
      <p>以上名称及金额由服务端从真实资料解析。确认时会再次检查，任何一张失败，整批都不保存。</p>
    </template>
    <template #footer><el-button :disabled="busy" @click="visible = false">关闭</el-button><el-button type="primary" :loading="busy" :disabled="!plan || uncertain" @click="commit">确认导入 {{ plan?.documentCount || 0 }} 张草稿</el-button></template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, shallowRef, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { receiptWorkflow as api, type ReceiptImportPlan } from '@/apis/finance/receiptWorkflow'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import { downloadExportBlob } from '@/utils/reportMappers'
const visible = defineModel<boolean>({ default: false })
const emit = defineEmits<{ saved: [ids: string[]] }>()
const file = shallowRef<File>(), plan = shallowRef<ReceiptImportPlan>(), error = ref(''), busy = ref(false), uncertain = ref(false)
const previewRows = computed(() => plan.value?.references.map(row => ({ ...row, date: plan.value?.documents.find(document => document.number === row.number)?.time || '' })) || [])
watch(visible, value => { if (value) { file.value = undefined;plan.value = undefined;error.value = '';uncertain.value = false } })
function beforeClose(done: () => void) { if (!busy.value) done() }
async function downloadTemplate() { if (busy.value) return;busy.value = true;error.value = '';try { downloadExportBlob(await api.template(), '客户收款导入模板.xlsx') } catch (failure) { error.value = extractErrorMessage(failure) } finally { busy.value = false } }
async function preview() { if (busy.value || !file.value) return;const selected = file.value;busy.value = true;error.value = '';plan.value = undefined;try { const result = await api.previewFile(selected);if (file.value === selected) { plan.value = result;uncertain.value = false } } catch (failure) { error.value = extractErrorMessage(failure) } finally { busy.value = false } }
async function selectFile(event: Event) { const input = event.target as HTMLInputElement, selected = input.files?.[0];input.value = '';if (!selected || busy.value) return;plan.value = undefined;file.value = undefined;error.value = '';uncertain.value = false;if (!selected.size || selected.size > 5 * 1024 * 1024) { error.value = '请选择非空Excel模板，最大5MiB';return }file.value = selected;await preview() }
async function commit() {
  if (busy.value || !plan.value || !file.value || uncertain.value) return
  const reviewed = plan.value, selected = file.value
  try { await ElMessageBox.confirm(`将保存${reviewed.documentCount}张收款草稿、${reviewed.lineCount}条明细，合计${reviewed.cash}。不会自动入账或增加余额。`, '确认导入收款草稿', { type: 'warning' }) } catch { return }
  if (busy.value || plan.value !== reviewed || file.value !== selected || uncertain.value) { error.value = '模板或预览已变化，请重新预览核对';return }
  busy.value = true;error.value = ''
  try { const result = await api.importFile(selected, reviewed.version);plan.value = undefined;visible.value = false;emit('saved', result.ids);ElMessage.success(`已保存${result.documentCount}张收款草稿，请打开单据核对后确认收款`) }
  catch (failure) { uncertain.value = true;error.value = extractErrorMessage(failure) + '；本次导入未确认，请先按单据编号查询结果，再重新预览核对，避免重复导入。' }
  finally { busy.value = false }
}
</script>

<style scoped>
.actions,.summary{display:flex;flex-wrap:wrap;align-items:center;gap:16px;margin:18px 0}.summary{padding:16px;background:#eff8f4;border-radius:8px}p{line-height:1.8;color:#526176}small{display:block;color:#6d7b89;margin-top:4px}label{display:flex;align-items:center;gap:8px}
</style>
