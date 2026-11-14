<template>
  <div class="inventory-summary area">
    <div class="layout">
      <!-- 使用 GoodSearchForm 组件 -->
      <GoodSearchForm 
        v-model="searchForm"
        :config="searchConfig"
        @search="handleSearch"
      />
      
      <!-- 操作按钮 -->
      <div class="operation-buttons">
        <el-button class="white-button" @click="handleExport">导出</el-button>
        <el-button class="white-button" @click="handleReload">刷新</el-button>
      </div>
    </div>

    <el-divider></el-divider>

    <el-table
      :data="tableData"
      height="calc(100% - 90px)"
      border
      v-loading="loading"
    >
      <!-- 固定列：商品信息 -->
      <el-table-column 
        prop="goodsData.name" 
        label="商品名称" 
        align="center" 
        width="160px" 
        fixed="left"
      ></el-table-column>
      <el-table-column 
        prop="goodsData.number" 
        label="商品编号" 
        align="center" 
        width="120px"
      ></el-table-column>
      <el-table-column 
        prop="goodsData.spce" 
        label="规格型号" 
        align="center" 
        width="90px"
      ></el-table-column>
      <el-table-column 
        prop="unit" 
        label="单位" 
        align="center" 
        width="90px"
      ></el-table-column>

      <!-- 动态列：各仓库列 -->
      <el-table-column 
        v-for="column in tableColumn" 
        :key="column.id"
        :label="column.name" 
        align="center"
      >
        <el-table-column 
          :prop="`wb_${column.id}.uct`" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row[`wb_${column.id}`]?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          :prop="`wb_${column.id}.uns`" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row[`wb_${column.id}`]?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          :prop="`wb_${column.id}.bct`" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row[`wb_${column.id}`]?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 汇总列 -->
      <el-table-column label="汇总" align="center">
        <el-table-column 
          prop="balance.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.balance?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="balance.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.balance?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="balance.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.balance?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>
    </el-table>

    <el-pagination
      class="tablePagination"
      v-model:current-page="pagination.pageIndex"
      v-model:page-size="pagination.pageSize"
      :total="pagination.total"
      :page-sizes="[30, 60, 90, 150, 300]"
      :pager-count="5"
      layout="prev, pager, next, jumper, sizes, total"
      @size-change="handlePageSizeChange"
      @current-change="handlePageChange"
    >
    </el-pagination>

    <!-- 统计信息 -->
    <div class="table-summary">
      <span>总成本：{{ formatNumber(totalCost) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import GoodSearchForm from '@/components/goodSearchConpoent'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent'
import { WarehouseReportAPI } from '@/apis/report/warehouse'
import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'

/**
 * 类型定义
 */
interface TableColumn { id: string; name: string }

interface GoodsData {
  name: string
  number: string
  spce: string
}

interface WarehouseBalance {
  uct: number  // 单位成本
  uns: number  // 数量
  bct: number  // 总成本
}

interface TableRow {
  goodsData: GoodsData
  unit: string
  balance: WarehouseBalance
  [key: string]: any  // 动态仓库字段 wb_${id}]
}

/**
 * 响应式数据
 */
const searchForm = ref<SearchFormData>({
  goods: '',
  warehouse: null,
  time: getCurrentDate()
})

const searchConfig: GoodSearchConfig = {
  inline: true,
  showGoods: true,
  showWarehouse: true,
  showNumber: false,
  showSupplier: false,
  showCustomer: false,
  showPeople: false,
  showUser: false,
  showExamine: false,
  showState: false,
  showRemark: false,
  showBillDate: false,
  showArrivalDate: false,
  customFields: [
    { key: 'time', type: 'date', label: '日期' }
  ]
}

const tableData = ref<TableRow[]>([])
const tableColumn = ref<TableColumn[]>([])
const loading = ref(false)

const pagination = reactive({
  pageIndex: 1,
  pageSize: 30,
  total: 0
})

/**
 * 导出相关数据
 */
const exportFileName = ref('商品库存余额表')
const exportDataList = computed(() => {
  // 将表格数据转换为导出格式
  return tableData.value.map(row => {
    const exportRow: any = {
      '商品名称': row.goodsData?.name || '',
      '商品编号': row.goodsData?.number || '',
      '规格型号': row.goodsData?.spce || '',
      '单位': row.unit || ''
    }
    
    // 添加各仓库数据
    tableColumn.value.forEach(col => {
      const warehouseData = row[`wb_${col.id}`]
      if (warehouseData) {
        exportRow[`${col.name}-成本`] = warehouseData.uct || 0
        exportRow[`${col.name}-数量`] = warehouseData.uns || 0
        exportRow[`${col.name}-总成本`] = warehouseData.bct || 0
      }
    })
    
    // 添加汇总数据
    exportRow['汇总-数量'] = row.balance?.uns || 0
    exportRow['汇总-成本'] = row.balance?.bct || 0
    
    return exportRow
  })
})

/**
 * 计算属性：总成本
 */
const totalCost = computed(() => {
  return tableData.value.reduce((sum, row) => {
    return sum + (row.balance?.bct || 0)
  }, 0)
})

/**
 * 初始化
 */
onMounted(() => {
  loadData(1)
})

/**
 * 获取当前日期
 */
function getCurrentDate(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function mapBalanceRow(item: Record<string, unknown>): TableRow {
  const row: TableRow = {
    goodsData: {
      name: String(item.productName ?? ''),
      number: String(item.productCode ?? ''),
      spce: String(item.specification ?? '')
    },
    unit: String(item.unit ?? ''),
    balance: {
      uct: Number(item.avgCost) || 0,
      uns: Number(item.sumQty) || 0,
      bct: Number(item.sumAmount) || 0
    }
  }
  const cells = Array.isArray(item.cells) ? item.cells : []
  cells.forEach((cell: Record<string, unknown>) => {
    const id = String(cell.warehouseId ?? cell.warehouseName ?? '')
    if (!id) return
    row[`wb_${id}`] = {
      uct: Number(cell.cost) || 0,
      uns: Number(cell.qty) || 0,
      bct: Number(cell.amount) || 0
    }
  })
  return row
}

function buildBalanceParams(): Record<string, unknown> {
  const params: Record<string, unknown> = {
    pageIndex: pagination.pageIndex,
    pageSize: pagination.pageSize
  }
  if (searchForm.value.goods) params.productName = searchForm.value.goods
  if (searchForm.value.warehouse) params.warehouseId = searchForm.value.warehouse
  if (searchForm.value.time) params.queryDate = searchForm.value.time
  return params
}

async function loadData(page?: number) {
  if (page !== undefined) {
    pagination.pageIndex = page
  }

  loading.value = true

  try {
    const res = await WarehouseReportAPI.balanceList(buildBalanceParams())
    const { rows, total } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    const colMap = new Map<string, TableColumn>()
    rows.forEach((raw) => {
      const item = raw as Record<string, unknown>
      const cells = Array.isArray(item.cells) ? item.cells : []
      cells.forEach((cell: Record<string, unknown>) => {
        const id = String(cell.warehouseId ?? '')
        if (id && !colMap.has(id)) {
          colMap.set(id, { id, name: String(cell.warehouseName ?? id) })
        }
      })
    })
    tableColumn.value = Array.from(colMap.values())
    tableData.value = rows.map((item) => mapBalanceRow(item as Record<string, unknown>))
    pagination.total = total
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    tableColumn.value = []
    pagination.total = 0
    ElMessage.error(error instanceof Error ? error.message : '加载库存余额失败')
  } finally {
    loading.value = false
  }
}

/**
 * 处理搜索
 */
function handleSearch(formData: SearchFormData) {
  searchForm.value = formData
  loadData(1)
}

/**
 * 处理页码变化
 */
function handlePageChange(page: number) {
  loadData(page)
}

/**
 * 处理每页条数变化
 */
function handlePageSizeChange() {
  loadData(1)
}

/**
 * 导出数据
 */
async function handleExport() {
  try {
    ElMessage.info('正在导出商品库存余额表')
    const blob = await WarehouseReportAPI.balanceExport(buildBalanceParams())
    downloadExportBlob(blob, `${exportFileName.value}_${getCurrentDate()}.xlsx`)
    ElMessage.success('数据已刷新')
  } catch (error: unknown) {
    console.error('导出失败:', error)
    ElMessage.error(error instanceof Error ? error.message : '导出失败，请稍后重试')
  }
}

/**
 * 刷新页面
 */
function handleReload() {
  searchForm.value = {
    goods: '',
    warehouse: null,
    time: getCurrentDate()
  }
  loadData(1)
  ElMessage.success('数据已刷新')
}

/**
 * 格式化数字
 */
function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null) return '-'
  return value.toFixed(2)
}
</script>

<style scoped lang="scss">
.inventory-summary {
  height: 100%;
  display: flex;
  flex-direction: column;

  .layout {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .table-summary {
    margin-top: 10px;
    padding: 10px;
    background-color: #f5f7fa;
    border-radius: 4px;
    font-weight: bold;
    
    span {
      margin-right: 20px;
    }
  }

  .operation-buttons {
    display: flex;
    align-items: center;
    gap: 8px;

    .white-button {
      background-color: #ffffff;
      border-color: #dcdfe6;
      color: #606266;

      &:hover {
        background-color: #f5f7fa;
        border-color: #c0c4cc;
        color: #409eff;
      }

      &:active {
        background-color: #ecf5ff;
        border-color: #409eff;
        color: #409eff;
      }
    }
  }
}

.area {
  padding: 20px;
  box-sizing: border-box;
}

.tablePagination {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
</style>

