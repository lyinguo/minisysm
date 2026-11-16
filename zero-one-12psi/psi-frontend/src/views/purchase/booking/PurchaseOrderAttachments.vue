<template>
  <section class="order-attachments" aria-label="采购订单附件">
    <h3>订单附件 <small>{{ items.length }}/10</small></h3>
    <p>附件上传、移除后立即保存。单个文件最大5MiB，每张订单最多10个有效附件。</p>
    <p v-if="disabled" class="hint">已审核的订单只可下载；有未保存修改时，请先保存并重新打开详情，再操作附件。</p>
    <p v-if="legacy" class="hint">这张订单有历史附件字段，尚未迁移为可下载文件，请核对原文件后重新上传。</p>
    <label class="upload-label">上传附件<input aria-label="选择订单附件" type="file" :disabled="disabled || busy || items.length >= 10" @change="upload" /></label>
    <el-alert v-if="error" type="error" :title="error" :closable="false" show-icon />
    <p v-if="!items.length">暂无已保存附件</p>
    <ul v-else>
      <li v-for="item in items" :key="item.id">
        <div class="file-info"><strong>{{ item.name }}</strong><small>{{ (item.size / 1024).toFixed(1) }} KiB · {{ item.uploadedAt }} · {{ item.uploaderName || '上传人资料缺失' }}</small></div>
        <el-button :disabled="busy" link type="primary" @click="download(item)">下载</el-button>
        <el-button :disabled="disabled || busy" link type="danger" @click="remove(item)">移除</el-button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { PurchaseOrderAPI, type PurchaseOrderAttachment, type PurchaseOrderAttachmentResult } from '@/apis/purchase/PurchaseBooking/order'
const props = defineProps<{orderId:string;version:string;items:PurchaseOrderAttachment[];disabled:boolean;legacy?:boolean}>()
const emit = defineEmits<{updated:[value:PurchaseOrderAttachmentResult];busy:[value:boolean]}>()
const busy = ref(false), error = ref('')
function pending(value:boolean) { busy.value=value;emit('busy',value) }
function failed(e:unknown) { error.value=e instanceof Error?e.message:'附件操作失败，请重新打开详情核对' }
async function upload(event:Event) {
  const input=event.target as HTMLInputElement, file=input.files?.[0]
  input.value=''
  if (!file || props.disabled || busy.value) return
  error.value='';pending(true)
  try { emit('updated',await PurchaseOrderAPI.uploadAttachment(props.orderId,props.version,file)) }
  catch(e) { failed(e) } finally { pending(false) }
}
async function remove(item:PurchaseOrderAttachment) {
  if (props.disabled || busy.value) return
  pending(true);error.value=''
  try {
    await ElMessageBox.confirm(`移除“${item.name}”？移除后不能从订单下载，系统会保留操作记录。`,'移除订单附件',{confirmButtonText:'移除',cancelButtonText:'取消',type:'warning'})
    emit('updated',await PurchaseOrderAPI.removeAttachment(props.orderId,item.id,props.version))
  } catch(e) { if(e!=='cancel' && e!=='close')failed(e) } finally { pending(false) }
}
async function download(item:PurchaseOrderAttachment) {
  if(busy.value)return
  pending(true);error.value=''
  try {
    const blob=await PurchaseOrderAPI.downloadAttachment(props.orderId,item.id)
    const url=URL.createObjectURL(blob), link=document.createElement('a')
    link.href=url;link.download=item.name;document.body.appendChild(link);link.click();link.remove()
    setTimeout(()=>URL.revokeObjectURL(url),10000)
  } catch(e) { failed(e) } finally { pending(false) }
}
</script>

<style scoped>
.order-attachments{margin-top:16px;padding:16px;border:1px solid #dce3ec;border-radius:8px;min-width:0}.order-attachments h3{margin:0 0 8px}.order-attachments p,.order-attachments small{color:#606b7a;font-size:13px}.upload-label{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:12px 0}.order-attachments ul{padding:0;list-style:none}.order-attachments li{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid #edf0f5}.file-info{flex:1;min-width:0;overflow-wrap:anywhere}.file-info small{display:block;margin-top:4px}.hint{line-height:1.6}
</style>
