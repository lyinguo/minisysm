<template>
  <!-- 主弹窗 -->
  <el-dialog v-model="visible" title="选择商品" width="92%" class="operation-pop-dialog" @closed="emit('close')">
    <div class="product-search-row"><el-input v-model="keyword" placeholder="名称 / 编号 / 条码" clearable @keyup.enter="search" /><el-button type="primary" @click="search">查询商品</el-button><span>选择实际商品，数量可在开单前调整</span></div>
    <!-- 表格 -->
    <div class="table-container">
      <el-table
        ref="mainTable"
        v-loading="loading"
        :data="filteredData"
        row-key="id"
        border
        style="width: 100%"
        @expand-change="handleExpandChange"
        empty-text="没有找到商品，请调整搜索条件，或前往商品管理新增"
      >
        <!-- 展开行的子表格 -->
        <template #default-expand-row="{ row }">
          <div v-if="row.children && row.children.length > 0" class="child-table-wrapper">
            <el-table
              :data="row.children"
              row-key="id"
              border
              style="width: 100%"
              @selection-change="(selection) => handleChildSelectChange(row, selection)"
            >
              <el-table-column type="selection" width="50" />
              <el-table-column prop="name" label="子商品名称" width="150" />
              <el-table-column prop="code" label="商品编号" />
              <el-table-column prop="model" label="规格型号" />
              <el-table-column prop="category" label="商品分类" />
              <el-table-column prop="unit" label="商品单位" />
              <el-table-column prop="purchasePrice" label="采购价格" />
              <el-table-column prop="salePrice" label="销售价格" />
              <el-table-column label="数量" width="100">
                <template #default="{ row: childRow }">
                  <el-input-number
                    v-model="childRow.quantity"
                    :min="1"
                    :controls="false"
                    size="small"
                    style="width: 80px"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
        <!-- 合并了展开功能的选择列（放在最左侧并固定） -->
        <el-table-column width="50" align="center" fixed="left">
          <template #default="{ row }">
            <!-- 无子数据时显示勾选框 -->
            <template v-if="!row.children || row.children.length === 0">
              <el-checkbox
                v-model="row._checked"
                @change="handleSingleSelect(row)"
                size="small"
              />
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="商品名称" min-width="210" fixed="left" show-overflow-tooltip />
        <el-table-column prop="code" label="商品编号" min-width="170" show-overflow-tooltip />
        <el-table-column prop="model" label="规格型号" min-width="120" show-overflow-tooltip />
        <el-table-column prop="category" label="商品分类" min-width="110" show-overflow-tooltip />
        <el-table-column prop="brand" label="商品品牌" min-width="120" show-overflow-tooltip />
        <el-table-column prop="unit" label="商品单位" width="95" />
        <el-table-column prop="purchasePrice" label="采购价格" width="110" align="right" />
        <el-table-column prop="salePrice" label="销售价格" width="110" align="right" />
        <el-table-column prop="barcode" label="商品条码" min-width="185" show-overflow-tooltip />
        <el-table-column label="数量" width="100" fixed="right">
          <template #default="{ row }">
            <el-input-number
              v-model="row.quantity"
              :min="1"
              :controls="false"
              size="small"
              style="width: 80px"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[30, 60, 90]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
      />
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="showSearchButton" @click="toggleSearchPopup">
          <el-icon><MoreFilled /></el-icon><span>更多筛选</span>
        </el-button>

        <div class="right-buttons">
          <el-button v-if="mainSelectedItems.length || childSelectedItems.size" @click="clearSelection">清空已选</el-button>
          <el-button @click="cancel">取消</el-button>
          <el-button type="primary" :disabled="!mainSelectedItems.length && !childSelectedItems.size" @click="handleConfirm">确认选择（{{ mainSelectedItems.length + [...childSelectedItems.values()].reduce((count, rows) => count + rows.length, 0) }}）</el-button>
          <el-button type="success" @click="addItem">去商品管理新增</el-button>
        </div>
      </div>
    </template>

    <!-- 内嵌搜索小弹窗 -->
    <div class="search-popup-container" v-if="showSearchPopup">
      <SearchPopup
        :options="selectOptions"
        @close="showSearchPopup = false"
        @search="handleSearch"
      />
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { MoreFilled } from '@element-plus/icons-vue'
import { useHttp } from '@/plugins/http'
import { extractErrorMessage } from '@/apis/utils/jsonResponse'
import SearchPopup from './SearchPopup.vue'
const props = defineProps({ showSearchButton: { type: Boolean, default: true } })
const emit = defineEmits(['confirm', 'close'])
const http = useHttp()
const visible = ref(true)
const loading = ref(false)
const keyword = ref('')
const filters = ref<Record<string, any>>({})
const filteredData = ref<any[]>([])
const total = ref(0)
const pagination = ref({ page: 1, pageSize: 30 })
const mainTable = ref()
const mainSelectedItems = ref<any[]>([])
const childSelectedItems = ref(new Map<string, any[]>())
const expandedRows = ref<string[]>([])
const showSearchPopup = ref(false)
const selectOptions = ref({ categories: [] as string[], brands: [] as string[], types: [] as string[] })
let requestSequence = 0
async function loadProducts() {
  const sequence = ++requestSequence
  loading.value = true
  mainSelectedItems.value = mainSelectedItems.value.map(selected => filteredData.value.find(row => row.id === selected.id && row._checked) || selected)
  try {
    const response = await http.get<any>('/goods/query-list', {
      pageIndex: pagination.value.page, pageSize: pagination.value.pageSize,
      keyword: keyword.value.trim() || undefined, brand: filters.value.brand || undefined,
      category: filters.value.categoryId || undefined, spec: filters.value.type || undefined
    })
    if (sequence !== requestSequence) return
    if (response.code !== 10000) throw new Error(response.message || '商品加载失败')
    filteredData.value = (response.data?.rows || []).map((row: any) => ({
      ...row, id: String(row.id), code: row.number, model: row.spec || '',
      categoryId: row.category, category: row.categoryName || (row.category && row.category !== '0' ? row.category : '未分类'),
      barcode: row.code || '', purchasePrice: row.buy ?? 0, salePrice: row.sell ?? 0,
      quantity: mainSelectedItems.value.find(selected => selected.id === String(row.id))?.quantity || 1,
      _checked: mainSelectedItems.value.some(selected => selected.id === String(row.id))
    }))
    total.value = Number(response.data?.total || 0)
    selectOptions.value = {
      categories: [...new Set(filteredData.value.map(row => String(row.category || '')).filter(Boolean))],
      brands: [...new Set(filteredData.value.map(row => String(row.brand || '')).filter(Boolean))],
      types: [...new Set(filteredData.value.map(row => String(row.model || '')).filter(Boolean))]
    }
  } catch (error) {
    if (sequence !== requestSequence) return
    filteredData.value = []
    total.value = 0
    ElMessage.error(extractErrorMessage(error))
  } finally { if (sequence === requestSequence) loading.value = false }
}
function search() {
  if (pagination.value.page !== 1) pagination.value.page = 1
  else void loadProducts()
}
function handleSearch(value: Record<string, any>) {
  filters.value = { ...value, categoryId: filteredData.value.find(row => row.category === value.category)?.categoryId || (value.category === filters.value.category ? filters.value.categoryId : undefined) }
  keyword.value = value.keyword || ''
  showSearchPopup.value = false
  search()
}
function handleSingleSelect(row: any) {
  const index = mainSelectedItems.value.findIndex(selected => selected.id === row.id)
  if (row._checked && index < 0) mainSelectedItems.value.push(row)
  else if (!row._checked && index >= 0) mainSelectedItems.value.splice(index, 1)
}
function clearSelection() {
  mainSelectedItems.value = []
  childSelectedItems.value.clear()
  filteredData.value.forEach(row => { row._checked = false })
}
function handleChildSelectChange(parent: any, rows: any[]) {
  if (rows.length) childSelectedItems.value.set(String(parent.id), rows)
  else childSelectedItems.value.delete(String(parent.id))
}
function handleExpandChange(row: any, expanded: any) {
  const id = String(row.id)
  if (expanded && !expandedRows.value.includes(id)) expandedRows.value.push(id)
  else if (!expanded) expandedRows.value = expandedRows.value.filter(value => value !== id)
}
function handleConfirm() {
  const selected = [...mainSelectedItems.value.map(row => {
    const current = filteredData.value.find(value => value.id === row.id)
    return { ...row, quantity: current?.quantity || row.quantity || 1 }
  }), ...[...childSelectedItems.value.entries()].flatMap(([parentId, rows]) => rows.map(row => ({ ...row, parentId })))]
  if (!selected.length) { ElMessage.warning('请先选择商品'); return }
  emit('confirm', selected)
  visible.value = false
}
function cancel() { visible.value = false }
function addItem() { window.open('/product-manage', '_blank', 'noopener') }
function toggleSearchPopup() { showSearchPopup.value = !showSearchPopup.value }
watch(() => [pagination.value.page, pagination.value.pageSize], loadProducts)
onMounted(loadProducts)
</script>

<style scoped>
.table-container {
  overflow-x: auto;
  max-height: 400px;
}
.pagination-container {
  text-align: center;
  margin-top: 10px;
}
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.right-buttons {
  display: flex;
  gap: 10px;
}
.search-popup-container {
  position: absolute;
  bottom: 20px;
  left: 20px;
  z-index: 3001;
}
/* 移除不再使用的expand-button样式 */
/* 自定义展开行样式 */
:deep(.el-table__expanded-cell) {
  padding: 0 !important;
  background-color: #fafafa;
}
.child-table-wrapper {
  padding: 10px;
}
.child-table {
  width: 100%;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  overflow: hidden;
}
/* 固定列样式调整 */
:deep(.el-table__fixed-left) {
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.1);
  z-index: 4;
}
/* 确保两个固定列之间无缝连接 */
:deep(.el-table__fixed-left:last-child) {
  box-shadow: 2px 0 6px rgba(0, 21, 41, 0.1);
  z-index: 3;
}
</style>

<style scoped>.product-search-row{display:flex;gap:10px;align-items:center;margin-bottom:16px}.product-search-row .el-input{width:280px}.product-search-row>span{font-size:12px;color:#8490a3}@media(max-width:600px){.product-search-row{flex-wrap:wrap}.product-search-row .el-input{width:100%}.right-buttons{flex-wrap:wrap}}</style>
