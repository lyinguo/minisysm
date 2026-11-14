<!--
 * 供应商选择：打开即加载列表，支持名称/编号筛选后点选
-->
<template>
  <div class="supplier-search-container">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        clearable
        placeholder="输入名称或编号筛选"
        style="width: 260px"
        @keyup.enter="loadList"
      />
      <el-button type="primary" :loading="loading" @click="loadList">查询</el-button>
      <el-button @click="resetAndLoad">重置</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="searchResults"
      stripe
      highlight-current-row
      max-height="360"
      style="width: 100%; margin-top: 12px"
      @row-click="handleRowClick"
    >
      <el-table-column prop="name" label="供应商名称" min-width="160" />
      <el-table-column prop="code" label="供应商编号" width="140" />
      <el-table-column prop="category" label="类别" width="120" />
    </el-table>

    <div v-if="!loading && hasSearched && searchResults.length === 0" class="no-results">
      <el-empty description="暂无供应商，请先在基础资料中新增" :image-size="72" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { SupplierAPI } from '@/apis/basicdata/supplier'

const props = defineProps<{
  pagination?: { pageIndex: number; pageSize: number }
}>()

const emit = defineEmits<{
  search: [params: any]
}>()

const keyword = ref('')
const loading = ref(false)
const hasSearched = ref(false)
const searchResults = ref<Array<{ id: string; name: string; code: string; category: string }>>([])

async function loadList() {
  loading.value = true
  hasSearched.value = true
  try {
    const pageIndex = props.pagination?.pageIndex || 1
    const pageSize = props.pagination?.pageSize || 200
    const kw = keyword.value.trim()
    const result = await SupplierAPI.getSupplierList({
      pageIndex,
      pageSize,
      name: kw || undefined,
      code: kw || undefined
    })
    const rows = result?.data?.rows || []
    searchResults.value = rows.map((row: any) => ({
      id: String(row.id ?? ''),
      name: row.name || '',
      code: row.number || row.code || '',
      category: row.category || ''
    }))
  } catch (error) {
    console.error('搜索供应商失败:', error)
    searchResults.value = []
    ElMessage.error(error instanceof Error ? error.message : '加载供应商失败')
  } finally {
    loading.value = false
  }
}

function resetAndLoad() {
  keyword.value = ''
  loadList()
}

function handleRowClick(row: { id: string; name: string; code: string }) {
  if (!row?.id) {
    ElMessage.warning('该供应商缺少ID，无法选用')
    return
  }
  emit('search', {
    id: row.id,
    name: row.name,
    code: row.code,
    supplierName: row.name,
    supplierId: row.id
  })
  ElMessage.success(`已选择供应商：${row.name}`)
}

onMounted(() => {
  loadList()
})

defineExpose({
  triggerSearch: loadList,
  resetSearch: resetAndLoad
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}
.no-results {
  margin-top: 12px;
}
</style>
