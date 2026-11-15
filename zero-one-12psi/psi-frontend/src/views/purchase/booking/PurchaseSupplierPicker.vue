<template>
  <section class="supplier-step" :class="{ invalid }" aria-label="采购订单供应商">
    <div class="supplier-step-title"><strong><span class="required">*</span> {{ title }}</strong><span>{{ description }}</span></div>
    <div class="supplier-choice">
      <el-button type="primary" :disabled="disabled" @click="openPicker">{{ supplierId ? '更换供应商' : '选择供应商' }}</el-button>
      <strong v-if="supplierId" class="chosen-name">{{ supplierName || '已选择供应商' }}</strong>
      <span v-else class="unselected">尚未选择供应商</span>
      <el-button v-if="supplierId && !disabled" link @click="emit('clear')">清除选择</el-button>
      <el-button v-if="!disabled" link type="primary" @click="manage">新增／维护供应商</el-button>
    </div>
    <p v-if="invalid && !supplierId" class="field-error" role="alert">请点击“选择供应商”，在列表中找到对应供应商后点击“选用”。</p>
    <el-dialog v-model="visible" title="选择采购订单供应商" width="min(780px, 94vw)" append-to-body :close-on-click-modal="false">
      <p>可按名称或编号查询。找到供应商后，点击该行右侧的“选用”。</p>
      <form class="supplier-filters" @submit.prevent="search">
        <el-input v-model="name" aria-label="供应商名称" placeholder="按供应商名称搜索" clearable />
        <el-input v-model="code" aria-label="供应商编号" placeholder="按供应商编号搜索" clearable />
        <el-button native-type="submit" type="primary" :loading="loading">查询供应商</el-button>
        <el-button @click="reset">重置</el-button>
      </form>
      <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon class="supplier-error"><el-button :disabled="loading" @click="load">重试加载供应商</el-button></el-alert>
      <el-table v-loading="loading" :data="rows" border max-height="340" class="supplier-table" empty-text="没有匹配的供应商，请调整条件或先新增供应商">
        <el-table-column prop="name" label="供应商名称" min-width="180" />
        <el-table-column prop="code" label="供应商编号" min-width="140" />
        <el-table-column label="操作" width="90" fixed="right"><template #default="{ row }"><el-button type="primary" link @click="choose(row)">选用</el-button></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="10" :total="total" layout="prev, pager, next, total" class="supplier-pagination" @current-change="load" />
      <template #footer><el-button @click="manage">没有找到？新增供应商</el-button><el-button @click="visible = false">取消</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { SupplierAPI } from '@/apis/basicdata/supplier'
interface Choice { id: string; name: string; code: string }
const props = withDefaults(defineProps<{ supplierId?: string | null; supplierName?: string; invalid?: boolean; disabled?: boolean; title?: string; description?: string }>(), { supplierId: null, supplierName: '', invalid: false, disabled: false, title: '第一步：选择供应商', description: '选择向谁采购，再填写商品和订单信息。' })
const emit = defineEmits<{ select: [choice: Choice]; clear: []; manage: [] }>()
const visible = ref(false)
const name = ref('')
const code = ref('')
const page = ref(1)
const total = ref(0)
const rows = ref<Choice[]>([])
const loading = ref(false)
const error = ref('')
let applied = { name: '', code: '' }
let sequence = 0
async function load() {
  const request = ++sequence
  loading.value = true; error.value = ''
  try {
    const result = await SupplierAPI.getSupplierList({ pageIndex: page.value, pageSize: 10, name: applied.name || undefined, code: applied.code || undefined })
    if (request !== sequence) return
    if (result.code !== 10000 || !Array.isArray(result.data?.rows)) throw new Error(result.message || '供应商加载失败，请重试')
    rows.value = result.data.rows.filter(item => item.id && item.name).map(item => ({ id: String(item.id), name: item.name, code: item.number || item.code || '' }))
    total.value = Number(result.data.total) || 0
  } catch (cause) {
    if (request !== sequence) return
    rows.value = []; total.value = 0
    error.value = cause instanceof Error ? cause.message : '供应商加载失败，请检查服务后重试'
  } finally { if (request === sequence) loading.value = false }
}
function search() { applied = { name: name.value.trim(), code: code.value.trim() }; page.value = 1; void load() }
function reset() { name.value = ''; code.value = ''; search() }
function openPicker() { if (props.disabled) return; visible.value = true; search() }
function choose(choice: Choice) { if (props.disabled || !choice.id) return; emit('select', choice); visible.value = false }
function manage() { if (props.disabled) return; visible.value = false; emit('manage') }
defineExpose({ openPicker })
</script>

<style scoped>
.supplier-step { padding: 16px; border: 1px solid #b6d7fc; border-radius: 8px; background: #f4f9ff; margin-bottom: 18px; }
.supplier-step-title, .supplier-choice { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.supplier-step-title { margin-bottom: 12px; }
.supplier-step-title > span, .unselected { color: #606266; font-size: 13px; }
.chosen-name { overflow-wrap: anywhere; }
.required, .field-error { color: #c45656; }
.invalid { border-color: #e29c9c; }
.field-error { margin: 10px 0 0; font-size: 13px; }
.supplier-filters { display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0; }
.supplier-filters .el-input { flex: 1 1 190px; }
.supplier-table, .supplier-pagination, .supplier-error { margin-top: 14px; }
.supplier-choice .el-button, .supplier-filters .el-button { margin-left: 0; }
</style>
