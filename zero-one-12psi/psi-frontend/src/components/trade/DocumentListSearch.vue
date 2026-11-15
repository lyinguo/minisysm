<template>
  <form class="document-search" @submit.prevent="search">
    <div class="primary-filters">
      <label>单据编号<el-input v-model="draft.number" placeholder="输入编号，支持部分匹配" clearable /></label>
      <label>{{ kind === 'sale' ? '客户' : '供应商' }}<el-input v-model="draft.counterparty" :placeholder="kind === 'sale' ? '输入客户名称或编号' : '输入供应商名称或编号'" clearable /></label>
      <label class="date-filter">单据日期<el-date-picker v-model="dates" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" range-separator="至" clearable /></label>
      <label>审核状态<el-select v-model="draft.examine" placeholder="全部状态" clearable><el-option label="未审核" :value="0" /><el-option label="已审核" :value="1" /></el-select></label>
      <div class="filter-buttons"><el-button native-type="submit" type="primary">查询</el-button><el-button @click="reset">重置</el-button><el-button link @click="advanced = !advanced">{{ advanced ? '收起筛选' : '更多筛选' }}</el-button></div>
    </div>
    <div v-if="advanced" class="advanced-filters">
      <label>商品名称<el-input v-model="draft.goods" placeholder="输入商品名称" clearable /></label>
      <label>关联人员<el-input v-model="draft.people" placeholder="输入人员名称" clearable /></label>
      <label>制单人<el-input v-model="draft.user" placeholder="输入姓名或账号" clearable /></label>
      <label>备注<el-input v-model="draft.data" placeholder="输入备注关键字" clearable /></label>
    </div>
    <p class="filter-hint">查询全部已保存单据；刷新保留查询条件。底部金额仅合计当前页。</p>
  </form>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
const props = withDefaults(defineProps<{ kind?: 'sale' | 'purchase' }>(), { kind: 'sale' })
const emit = defineEmits<{ search: [value: Record<string, any>] }>()
const advanced = ref(false)
const dates = ref<string[]>([])
const draft = reactive({ number: '', counterparty: '', examine: undefined as number | undefined, goods: '', people: '', user: '', data: '' })
function search() {
  if (dates.value?.length === 2 && dates.value[0] > dates.value[1]) { ElMessage.warning('开始日期不能晚于结束日期'); return }
  emit('search', {
    number: draft.number.trim(), [props.kind === 'sale' ? 'customer' : 'supplier']: draft.counterparty.trim(),
    examine: draft.examine, goods: draft.goods.trim(), people: draft.people.trim(), user: draft.user.trim(), data: draft.data.trim(),
    startTime: dates.value?.[0] || '', endTime: dates.value?.[1] || ''
  })
}
function reset() {
  Object.assign(draft, { number: '', counterparty: '', examine: undefined, goods: '', people: '', user: '', data: '' })
  dates.value = []
  search()
}
</script>

<style scoped>
.document-search{width:100%;padding:16px;background:#f8fafc;border:1px solid #e3eaf3;border-radius:10px}
.primary-filters,.advanced-filters{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap}
label{display:flex;flex-direction:column;gap:6px;font-size:13px;color:#435269;width:180px}.date-filter{width:290px}.date-filter :deep(.el-date-editor){width:100%}
.filter-buttons{display:flex;align-items:center;gap:8px;min-height:32px}.filter-buttons .el-button+.el-button{margin-left:0}.advanced-filters{margin-top:14px;padding-top:14px;border-top:1px solid #e3eaf3}.filter-hint{margin:12px 0 0;color:#718096;font-size:12px}
@media(max-width:600px){label,.date-filter{width:100%}.filter-buttons{width:100%}}
</style>
