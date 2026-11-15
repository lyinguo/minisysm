<template>
  <section class="purchase-entry" aria-label="按商品供应商采购">
    <el-alert type="info" :closable="false" show-icon title="先添加商品，再为每行选择供货商；保存时按供应商拆成独立采购订单。草稿不会直接入库或付款。" />
    <el-form inline class="entry-header" :disabled="saving">
      <el-form-item label="本次采购编号"><el-input v-model="header.documentNumber" maxlength="28" placeholder="本次采购编号" /></el-form-item>
      <el-form-item label="单据日期"><el-date-picker v-model="header.documentDate" value-format="YYYY-MM-DD" type="date" placeholder="单据日期" /></el-form-item>
      <el-form-item label="到货日期"><el-date-picker v-model="header.arrivalDate" value-format="YYYY-MM-DD" type="date" placeholder="到货日期" /></el-form-item>
    </el-form>
    <div class="entry-actions"><el-button type="primary" :disabled="saving" @click="productsOpen = true">添加商品</el-button><el-button :loading="saving" type="success" @click="save">按供应商拆单保存</el-button><el-button :disabled="saving" @click="router.push('/purchase-booking-report')">查询采购订单</el-button><el-button :disabled="saving" @click="router.push('/supplier-manage')">供应商资料</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-table :data="rows" border empty-text="点击“添加商品”开始采购" style="width:100%">
      <el-table-column type="index" label="序号" width="60" />
      <el-table-column prop="productName" label="商品" min-width="170"><template #default="{row}"><strong>{{row.productName}}</strong><small>{{row.productCode}}</small></template></el-table-column>
      <el-table-column label="本行供应商" min-width="250"><template #default="{row}">
        <el-select v-model="row.supplierId" placeholder="选择该商品的供货商" :disabled="saving" filterable clearable @change="id => selectSupplier(row,id)"><el-option v-for="supplier in activeSupply(row)" :key="supplier.id" :label="supplier.name" :value="supplier.id" /></el-select>
        <div class="supply-hint"><span v-if="supplyError[goodsId(row)]" class="error">{{supplyError[goodsId(row)]}}</span><span v-else-if="!activeSupply(row).length">尚无有效供货商</span><el-button link type="primary" :disabled="saving" @click="openSupply(row)">维护供货商</el-button><el-button v-if="supplyError[goodsId(row)]" link @click="loadSupply(row)">重试</el-button></div>
      </template></el-table-column>
      <el-table-column label="入库仓库" min-width="185"><template #default="{row}"><el-select v-model="row.warehouseId" placeholder="选择仓库" filterable :disabled="saving"><el-option v-for="warehouse in warehouses" :key="warehouse.id" :label="warehouse.name" :value="warehouse.id" /></el-select></template></el-table-column>
      <el-table-column prop="unit" label="单位" width="75" />
      <el-table-column label="单价" width="145"><template #default="{row}"><el-input-number v-model="row.price" :min="0" :precision="4" :controls="false" aria-label="单价" :disabled="saving" /></template></el-table-column>
      <el-table-column label="数量" width="145"><template #default="{row}"><el-input-number v-model="row.quantity" :min="0.0001" :precision="4" :controls="false" aria-label="数量" :disabled="saving" /></template></el-table-column>
      <el-table-column label="税率%" width="110"><template #default="{row}"><el-input-number v-model="row.taxRate" :min="0" :max="100" :precision="2" :controls="false" aria-label="税率" :disabled="saving" /></template></el-table-column>
      <el-table-column label="未税金额" width="125"><template #default="{row}">{{amounts(row).net.toFixed(4)}}</template></el-table-column>
      <el-table-column label="价税合计" width="125"><template #default="{row}">{{amounts(row).total.toFixed(4)}}</template></el-table-column>
      <el-table-column label="操作" width="80"><template #default="{$index}"><el-button link type="danger" :disabled="saving" @click="rows.splice($index,1)">移除</el-button></template></el-table-column>
    </el-table>
    <div v-if="warehouseError" class="error">{{warehouseError}} <el-button link @click="loadWarehouses">重新加载仓库</el-button></div>
    <el-input v-model="header.remarks" type="textarea" maxlength="256" placeholder="采购备注（可选）" :disabled="saving" />
    <section class="split-preview" aria-label="拆单预览"><h3>拆单预览</h3><p v-if="!groups.length">为每行商品选择供应商后，这里显示将生成的订单。</p><p v-for="(group,index) in groups" :key="group.id">{{header.documentNumber}}-{{String(index+1).padStart(3,'0')}} · {{group.name}} · {{group.rows.length}} 行 · 含税 {{group.total.toFixed(4)}} 元</p><p v-if="missingSuppliers">还有 {{missingSuppliers}} 行未选择有效供货商，不能保存。</p></section>
    <el-alert v-if="saved.length" type="success" :closable="false" title="以下订单已全部保存为未审核草稿。本次输入已清空，可以继续新增采购。" />
    <ul v-if="saved.length" aria-label="已生成采购订单"><li v-for="order in saved" :key="order.id">{{order.number}} · {{order.supplierName}} · {{order.lineCount}} 行 · 未审核</li></ul>
    <OperationPopTable v-if="productsOpen" @confirm="addProducts" @close="productsOpen = false" />
    <el-dialog v-model="supplyOpen" title="维护商品供货商" width="760px" destroy-on-close>
      <template v-if="supplyRow"><h3>{{supplyRow.productName}}</h3><p>请先向供应商确认可供货，再维护关系。只有已建立且启用的关系才能采购；停用不会删除已有订单。维护关系需要供货关系管理权限。</p>
        <PurchaseSupplierPicker title="为此商品关联供货商" description="选中实际供应商后，点击下方按钮建立供货关系。" :supplier-id="candidate.id" :supplier-name="candidate.name" @select="value => candidate = value" @clear="candidate = {id:'',name:''}" @manage="goManage" />
        <el-button type="primary" :loading="linking" @click="changeSupply(candidate.id,true)">建立并选用供货商</el-button>
        <el-alert v-if="linkError" :title="linkError" type="error" :closable="false" />
        <ul><li v-for="supplier in catalog[goodsId(supplyRow)] || []" :key="supplier.id">{{supplier.name}}（{{supplier.enabled ? '可供货' : '已停用'}}）<el-button link :disabled="linking" @click="changeSupply(supplier.id,!supplier.enabled)">{{supplier.enabled ? '停用' : '重新启用'}}</el-button></li></ul>
      </template>
    </el-dialog>
  </section>
</template>
<script setup lang="ts">
import {computed,onMounted,reactive,ref,watch} from 'vue'
import {useRouter} from 'vue-router'
import {usePurchaseStore} from '@/stores/purchase'
import {CommonAPI} from '@/apis/common/api'
import {PurchaseOrderAPI} from '@/apis/purchase/PurchaseBooking/order'
import {purchaseSelectionRows} from '@/utils/purchaseEntry'
import OperationPopTable from '@/components/operationpoptable/OperationPopTable.vue'
import PurchaseSupplierPicker from './PurchaseSupplierPicker.vue'
type Row = Record<string,any>
type Supplier = {id:string;name:string;number:string;enabled:number}
const router=useRouter(),store=usePurchaseStore()
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}
const newNumber=()=>`CG${Date.now()}${Math.random().toString(36).slice(2,7)}`
const cached=store.getPurchaseBookData
// Restore before the workspace can remount this page; never copy the old header supplier onto rows.
const header=reactive({documentNumber:cached?.headerForm.documentNumber || newNumber(),documentDate:cached?.headerForm.documentDate || today(),arrivalDate:cached?.headerForm.arrivalDate || today(),remarks:cached?.headerForm.remarks || ''})
const rows=ref<Row[]>(cached?.tableData.filter(row=>row.productName).map(row=>({...row})) || [])
const productsOpen=ref(false),saving=ref(false),error=ref(''),warehouseError=ref('')
const warehouses=ref<Array<{id:string;name:string}>>([])
const catalog=reactive<Record<string,Supplier[]>>({}),supplyError=reactive<Record<string,string>>({})
const supplyOpen=ref(false),supplyRow=ref<Row|null>(null),linking=ref(false),linkError=ref(''),candidate=ref<{id:string;name:string}>({id:'',name:''})
const saved=ref<Array<{id:string;number:string;lineCount:number;supplierName:string}>>([])
const goodsId=(row:Row)=>String(row.goodsId || row.key || '')
const round=(value:number)=>Number(value.toFixed(4))
function amounts(row:Row){const gross=round(Number(row.price)*Number(row.quantity)),discount=round(gross*Number(row.discount||0)/100),net=round(gross-discount),tax=round(net*Number(row.taxRate||0)/100);return {net,tax,total:round(net+tax),discount}}
const activeSupply=(row:Row)=>(catalog[goodsId(row)] || []).filter(s=>Number(s.enabled)===1)
const validSupplier=(row:Row)=>activeSupply(row).find(s=>s.id===row.supplierId)
const missingSuppliers=computed(()=>rows.value.filter(row=>!validSupplier(row)).length)
const groups=computed(()=>{
  const result=new Map<string,{id:string;name:string;rows:Row[];total:number}>()
  rows.value.forEach(row=>{const supplier=validSupplier(row);if(!supplier)return;const group=result.get(supplier.id)||{id:supplier.id,name:supplier.name,rows:[],total:0};group.rows.push(row);group.total=round(group.total+amounts(row).total);result.set(supplier.id,group)})
  return [...result.values()]
})
function persist(){store.savePurchaseBookData({headerForm:{...header,supplier:'',supplierId:''},tableData:rows.value.map(row=>({...row})),isAudited:false})}
watch([header,rows],persist,{deep:true,flush:'sync'})
async function loadWarehouses(){try{warehouseError.value='';warehouses.value=await CommonAPI.getWarehouseNameList()}catch(e){warehouseError.value=e instanceof Error?e.message:'仓库加载失败'}}
async function loadSupply(row:Row){const id=goodsId(row);try{supplyError[id]='';const result=await PurchaseOrderAPI.supply(id);if(result.code!==10000 || !Array.isArray(result.data))throw new Error(result.message || '供货关系加载失败');catalog[id]=result.data}catch(e){catalog[id]=[];supplyError[id]=e instanceof Error?e.message:'供货关系加载失败'}}
function addProducts(products:Row[]){const added=purchaseSelectionRows(products);rows.value.push(...added);productsOpen.value=false;added.forEach(row=>void loadSupply(row))}
function selectSupplier(row:Row,id:string){row.supplierName=activeSupply(row).find(s=>s.id===id)?.name || ''}
async function openSupply(row:Row){supplyRow.value=row;candidate.value={id:'',name:''};linkError.value='';supplyOpen.value=true;await loadSupply(row)}
function goManage(){persist();void router.push('/supplier-manage')}
async function changeSupply(id:string,enabled:boolean){if(linking.value || !supplyRow.value)return;if(!id){linkError.value='请先选择供应商';return}linking.value=true;linkError.value='';const row=supplyRow.value;try{const result=await PurchaseOrderAPI.setSupply(goodsId(row),id,enabled);if(result.code!==10000)throw new Error(result.message || '供货关系保存失败');await loadSupply(row);if(enabled){row.supplierId=id;selectSupplier(row,id)}else rows.value.filter(r=>goodsId(r)===goodsId(row)&&r.supplierId===id).forEach(r=>{r.supplierId='';r.supplierName=''})}catch(e){linkError.value=e instanceof Error?e.message:'供货关系保存失败'}finally{linking.value=false}}
async function save(){
  if(saving.value)return
  error.value=''
  try{
    if(!rows.value.length)throw new Error('请先添加商品')
    if(!header.documentNumber.trim() || header.documentNumber.trim().length>28)throw new Error('本次采购编号应为1到28个字符')
    if(!header.documentDate || !header.arrivalDate || header.arrivalDate<header.documentDate)throw new Error('请填写日期，到货日期不能早于单据日期')
    rows.value.forEach((row,index)=>{if(!validSupplier(row))throw new Error(`第${index+1}行请选择该商品的有效供货商`);if(!row.warehouseId)throw new Error(`第${index+1}行请选择仓库`);if(row.price==null || row.quantity==null || !Number.isFinite(Number(row.price)) || !Number.isFinite(Number(row.quantity)) || Number(row.price)<0 || Number(row.quantity)<=0)throw new Error(`第${index+1}行单价和数量无效`)})
    saving.value=true
    const names=new Map(groups.value.map(group=>[group.id,group.name]))
    const result=await PurchaseOrderAPI.split({number:header.documentNumber.trim(),time:header.documentDate,arrival:header.arrivalDate,data:header.remarks,rows:rows.value.map(row=>{const amount=amounts(row);return {supplier:row.supplierId,goods:goodsId(row),warehouse:row.warehouseId,unit:row.unit,attr:row.attr || '',price:Number(row.price),nums:Number(row.quantity),discount:Number(row.discount||0),tax:Number(row.taxRate||0),dsc:amount.discount,total:amount.net,tat:amount.tax,tpt:amount.total,data:row.remark || ''}})})
    if(result.code!==10000 || !Array.isArray(result.data) || !result.data.length)throw new Error(result.message || '整批保存失败，输入已保留')
    saved.value=result.data.map(order=>({...order,supplierName:names.get(order.supplier)||order.supplier}))
    rows.value=[];header.documentNumber=newNumber();header.remarks='';persist()
  }catch(e){error.value=e instanceof Error?e.message:'保存失败，输入已保留'}finally{saving.value=false}
}
onMounted(()=>{void loadWarehouses();rows.value.forEach(row=>void loadSupply(row))})
</script>
<style scoped>
.purchase-entry{padding:18px;display:flex;flex-direction:column;gap:16px;min-width:0}.entry-header{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px}.entry-header :deep(.el-form-item){margin:0}.entry-actions{display:flex;gap:10px;flex-wrap:wrap}.el-input-number{width:100%}small{display:block;color:#737d8c}.supply-hint{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px;color:#737d8c}.error{color:#c33737}.split-preview{padding:12px 18px;background:#f5f8fc;border-radius:8px}.split-preview h3{margin:0 0 10px}.split-preview p{margin:6px 0}
</style>
