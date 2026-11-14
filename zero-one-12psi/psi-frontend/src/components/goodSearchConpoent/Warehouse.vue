<!--
 * 仓库选择：打开即加载列表，支持名称/编号筛选后点选
-->
<template>
  <div class="warehouse-search-container">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        clearable
        placeholder="输入名称或编号筛选"
        style="width: 220px"
        @keyup.enter="loadList"
      />
      <el-button type="primary" :loading="loading" @click="loadList">查询</el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="searchResults"
      stripe
      highlight-current-row
      max-height="320"
      style="width: 100%; margin-top: 12px"
      @row-click="handleRowClick"
    >
      <el-table-column prop="name" label="仓库名称" min-width="140" />
      <el-table-column prop="code" label="仓库编号" width="120" />
      <el-table-column prop="address" label="地址" min-width="120" show-overflow-tooltip />
    </el-table>

    <div v-if="!loading && hasSearched && searchResults.length === 0" class="no-results">
      <el-empty description="暂无仓库，请先在基础资料中新增" :image-size="64" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { WarehouseAPI } from '@/apis/basicdata/warehouse'

const props = defineProps<{
  pagination?: { pageIndex: number; pageSize: number }
}>()

const emit = defineEmits<{
  search: [params: any]
  confirm: [params: any]
}>()

const keyword = ref('')
const loading = ref(false)
const hasSearched = ref(false)
const searchResults = ref<
  Array<{ id: string; name: string; code: string; number: string; address: string }>
>([])

async function loadList() {
  loading.value = true
  hasSearched.value = true
  try {
    const pageIndex = props.pagination?.pageIndex || 1
    const pageSize = props.pagination?.pageSize || 200
    const kw = keyword.value.trim()
    const result = await WarehouseAPI.getWarehouseList({
      pageIndex,
      pageSize,
      name: kw || undefined,
      number: kw || undefined
    })
    const rows = result?.data?.rows || []
    searchResults.value = rows.map((row: any) => ({
      id: String(row.id ?? ''),
      name: row.name || '',
      code: row.number || '',
      number: row.number || '',
      address: row.add || row.address || ''
    }))
  } catch (error) {
    console.error('搜索仓库失败:', error)
    searchResults.value = []
    ElMessage.error(error instanceof Error ? error.message : '加载仓库失败')
  } finally {
    loading.value = false
  }
}

function handleRowClick(row: { id: string; name: string; number: string }) {
  if (!row?.id) {
    ElMessage.warning('该仓库缺少ID，无法选用')
    return
  }
  const payload = {
    id: row.id,
    name: row.name,
    number: row.number,
    warehouseName: row.name,
    warehouseId: row.id
  }
  emit('confirm', payload)
  emit('search', payload)
  ElMessage.success(`已选择仓库：${row.name}`)
}

onMounted(() => {
  loadList()
})

defineExpose({
  triggerSearch: loadList
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
}
.no-results {
  margin-top: 8px;
}
</style>
