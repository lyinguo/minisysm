<template>
  <el-dialog :model-value="visible" title="从采购订单生成收货草稿" width="min(1100px,96vw)" append-to-body :close-on-click-modal="false" :show-close="!saving" :close-on-press-escape="!saving" @update:model-value="value => emit('update:visible',value)">
    <el-alert type="info" :closable="false" title="生成采购草稿不会直接入库或付款。未入库草稿会占用订单数量；请到采购单报表核对、审核，或删除未核对草稿释放数量。" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <div v-loading="loading">
      <p>来源订单：{{source.number || orderId}} · 供应商：{{source.supplierName || source.supplier}}</p>
      <el-form inline :disabled="saving"><el-form-item label="采购单编号"><el-input v-model="number" maxlength="32" placeholder="新采购单编号" /></el-form-item><el-form-item label="收货日期"><el-date-picker v-model="date" type="date" value-format="YYYY-MM-DD" placeholder="收货日期" /></el-form-item></el-form>
      <el-table :data="rows" border max-height="350" empty-text="没有可生成的订单明细">
        <el-table-column prop="name" label="商品" min-width="160" /><el-table-column prop="number" label="商品编号" min-width="150" /><el-table-column prop="warehouseName" label="仓库" min-width="150" />
        <el-table-column prop="nums" label="订单数量" width="100" /><el-table-column prop="handle" label="已入库" width="95" /><el-table-column prop="reserved" label="待入库占用" width="110" /><el-table-column prop="available" label="可生成" width="95" />
        <el-table-column label="本次数量" width="150"><template #default="{row}"><el-input-number v-model="row.requested" :min="0" :max="Number(row.available)" :precision="4" :controls="false" :disabled="saving || !Number(row.available)" aria-label="本次数量" style="width:100%" /></template></el-table-column>
        <el-table-column prop="price" label="单价" width="90" /><el-table-column prop="discountPercent" label="折扣%" width="90" /><el-table-column prop="taxPercent" label="税率%" width="90" />
      </el-table>
      <p v-if="rows.some(row => row.overReserved)" class="error">已有草稿数量超过订单，请先处理下方待入库采购单，不要继续重复生成。</p>
      <p>本次 {{selected.length}} 行 · 未税 {{totals.net.toFixed(4)}} 元 · 含税 {{totals.actual.toFixed(4)}} 元</p>
      <div v-if="drafts.length"><strong>已生成的待入库采购单</strong><div v-for="draft in drafts" :key="draft.id"><el-button link type="primary" @click="emit('open-draft',draft.number)">{{draft.number}} · 查看处理</el-button></div></div>
    </div>
    <template #footer><el-button :disabled="loading || saving" @click="load">刷新剩余数量</el-button><el-button :disabled="saving" @click="emit('update:visible',false)">取消</el-button><el-button type="primary" :loading="saving" :disabled="loading || !selected.length" @click="create">生成采购草稿</el-button></template>
  </el-dialog>
</template>
<script setup lang="ts">
import {computed,ref,watch} from 'vue'
import {PurchaseOrderAPI} from '@/apis/purchase/PurchaseBooking/order'
import {tradeDocumentDefaults} from '@/utils/tradeDocumentDefaults'
import {receivingAmounts} from '@/utils/receivingAmounts'
const props=defineProps<{visible:boolean;orderId:string}>()
const emit=defineEmits<{ 'update:visible':[value:boolean];created:[document:{id:string;number:string}];'open-draft':[number:string] }>()
const source=ref<Record<string,any>>({}),rows=ref<Record<string,any>[]>([]),drafts=ref<Array<{id:string;number:string}>>([])
const loading=ref(false),saving=ref(false),error=ref(''),number=ref(''),date=ref('')
let sequence=0
const selected=computed(()=>rows.value.filter(row=>Number(row.requested)>0))
const round=(value:number)=>Number(value.toFixed(4))
const totals=computed(()=>selected.value.reduce((sum,row)=>{const amount=receivingAmounts(Number(row.price),Number(row.requested),Number(row.discountPercent),Number(row.taxPercent));return {net:round(sum.net+amount.net),actual:round(sum.actual+amount.actual)}},{net:0,actual:0}))
async function load(){const request=++sequence;loading.value=true;error.value='';source.value={};rows.value=[];drafts.value=[];try{const response=await PurchaseOrderAPI.receivePreview(props.orderId);if(request!==sequence)return;if(response.code!==10000 || !response.data || !Array.isArray(response.data.items))throw new Error(response.message || '收货预览读取失败');source.value=response.data.header;const items:Record<string,any>[]=response.data.items.map(row=>({...row,requested:Number(row.available)}));items.forEach(row=>receivingAmounts(Number(row.price),Number(row.available),Number(row.discountPercent),Number(row.taxPercent)));rows.value=items;drafts.value=response.data.drafts || []}catch(e){if(request!==sequence)return;rows.value=[];error.value=e instanceof Error?e.message:'预览读取失败'}finally{if(request===sequence)loading.value=false}}
watch(()=>[props.visible,props.orderId],()=>{if(props.visible){const defaults=tradeDocumentDefaults('purchase');number.value=defaults.documentNumber;date.value=defaults.documentDate;void load()}else{++sequence;loading.value=false}},{immediate:true})
async function create(){if(saving.value || loading.value)return;error.value='';try{if(!selected.value.length || !number.value.trim() || !date.value)throw new Error('请填写新采购单编号、收货日期和本次数量');if(rows.value.some(row=>Number(row.requested)>Number(row.available) || Number(row.requested)<0))throw new Error('本次数量不能超过可生成数量');saving.value=true;const result=await PurchaseOrderAPI.receiveOrder({id:props.orderId,number:number.value.trim(),time:date.value,items:selected.value.map(row=>({id:String(row.id),nums:Number(row.requested)}))});if(result.code!==10000 || !result.data?.id)throw new Error(result.message || '采购草稿生成失败，输入已保留');emit('created',result.data)}catch(e){error.value=e instanceof Error?e.message:'生成失败，输入已保留'}finally{saving.value=false}}
</script>
<style scoped>.el-form{margin-top:12px}.error{color:#c33737}</style>
