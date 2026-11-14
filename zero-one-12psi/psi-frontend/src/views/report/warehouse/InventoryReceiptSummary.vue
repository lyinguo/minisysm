<template>
  <div class="inventory-receipt-summary area">
    <div class="layout">
      <!-- 使用 GoodSearchForm 组件 -->
      <GoodSearchForm 
        v-model="searchForm"
        :config="searchConfig"
        :default-days="0"
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
      <!-- 商品名称列 -->
      <el-table-column 
        prop="goodsData.name" 
        label="商品名称" 
        align="center" 
        width="160px"
        fixed="left"
      ></el-table-column>

      <!-- 仓库列 -->
      <el-table-column 
        prop="warehouseData.name" 
        label="仓库" 
        align="center" 
        width="100px"
        fixed="left"
      ></el-table-column>

      <!-- 商品编号 -->
      <el-table-column 
        prop="goodsData.number" 
        label="商品编号" 
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 规格型号 -->
      <el-table-column 
        prop="goodsData.spce" 
        label="规格型号" 
        align="center" 
        width="90px"
      ></el-table-column>

      <!-- 单位 -->
      <el-table-column 
        prop="unit" 
        label="单位" 
        align="center" 
        width="90px"
      ></el-table-column>

      <!-- 期初 -->
      <el-table-column label="期初" align="center">
        <el-table-column 
          prop="state.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.state?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="state.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.state?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="state.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.state?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 采购�?-->
      <el-table-column label="采购单" align="center">
        <el-table-column 
          prop="buy.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.buy?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="buy.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.buy?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="buy.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.buy?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 采购退货单 -->
      <el-table-column label="采购退货单" align="center">
        <el-table-column 
          prop="bre.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.bre?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="bre.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.bre?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="bre.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.bre?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 销售单 -->
      <el-table-column label="销售单" align="center">
        <el-table-column 
          prop="sell.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.sell?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="sell.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.sell?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="sell.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.sell?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 销售退货单 -->
      <el-table-column label="销售退货单" align="center">
        <el-table-column 
          prop="sre.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.sre?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="sre.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.sre?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="sre.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.sre?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 调拨单-出 -->
      <el-table-column label="调拨单-出" align="center">
        <el-table-column 
          prop="swapOut.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.swapOut?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="swapOut.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.swapOut?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="swapOut.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.swapOut?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 调拨单-入 -->
      <el-table-column label="调拨单-入" align="center">
        <el-table-column 
          prop="swapEnter.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.swapEnter?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="swapEnter.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.swapEnter?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="swapEnter.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.swapEnter?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 其它入库�?-->
      <el-table-column label="其它入库单" align="center">
        <el-table-column 
          prop="entry.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.entry?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="entry.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.entry?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="entry.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.entry?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 其它出库�?-->
      <el-table-column label="其它出库单" align="center">
        <el-table-column 
          prop="extry.uct" 
          label="成本" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.extry?.uct) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="extry.uns" 
          label="数量" 
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.extry?.uns) }}
          </template>
        </el-table-column>
        <el-table-column 
          prop="extry.bct" 
          label="总成本"
          align="center" 
          width="90px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.extry?.bct) }}
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 汇�?-->
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import GoodSearchForm from '@/components/goodSearchConpoent'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent'
import { WarehouseReportAPI } from '@/apis/report/warehouse'
import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'

function packBalance(price?: unknown, nums?: unknown, total?: unknown) {
  return {
    uct: Number(price) || 0,
    uns: Number(nums) || 0,
    bct: Number(total) || 0
  }
}

function mapSummaryRow(item: Record<string, unknown>): TableRow {
  return {
    goodsData: {
      name: String(item.name ?? ''),
      number: String(item.number ?? ''),
      spce: String(item.spec ?? '')
    },
    warehouseData: { name: String(item.warehouse ?? '') },
    unit: String(item.unit ?? ''),
    state: packBalance(item.roomPrice, item.roomNums, item.roomTotal),
    buy: packBalance(item.buyPrice, item.buyNums, item.buyTotal),
    bre: packBalance(item.brePrice, item.breNums, item.breTotal),
    sell: packBalance(item.sellPrice, item.sellNums, item.sellTotal),
    sre: packBalance(item.srePrice, item.sreNums, item.sreTotal),
    swapOut: packBalance(item.swapOutPrice, item.swapOutNums, item.swapOutTotal),
    swapEnter: packBalance(item.swapInPrice, item.swapInNums, item.swapInTotal),
    extry: packBalance(item.extryPrice, item.extryNums, item.extryTotal),
    entry: packBalance(item.entryPrice, item.entryNums, item.entryTotal),
    balance: packBalance(item.SumPrice, item.SumNums, item.SumTotal)
  }
}

function buildSummaryParams(): Record<string, unknown> {
  const params: Record<string, unknown> = {
    pageIndex: pagination.pageIndex,
    pageSize: pagination.pageSize
  }
  if (searchForm.value.goods) params.goods = searchForm.value.goods
  if (searchForm.value.warehouse) params.warehouse = searchForm.value.warehouse
  if (searchForm.value.startTime) params.startTime = searchForm.value.startTime
  if (searchForm.value.endTime) params.endTime = searchForm.value.endTime
  return params
}

/**
 * 类型定义
 */
interface GoodsData {
  name: string
  number: string
  spce: string
}

interface WarehouseData {
  name: string
}

interface BillData {
  uct: number
  uns: number
  bct: number
}

interface TableRow {
  goodsData: GoodsData
  warehouseData: WarehouseData
  unit: string
  state: BillData
  buy: BillData
  bre: BillData
  sell: BillData
  sre: BillData
  swapOut: BillData
  swapEnter: BillData
  entry: BillData
  extry: BillData
  balance: BillData
}

/**
 * 响应式数据
 */
const searchForm = ref<SearchFormData>({
  goods: '',
  warehouse: null,
  startTime: '',
  endTime: ''
})

const searchConfig: GoodSearchConfig = {
  inline: true,
  showGoods: true,
  showWarehouse: true,
  showBillDate: true,
  showNumber: false,
  showSupplier: false,
  showCustomer: false,
  showPeople: false,
  showUser: false,
  showExamine: false,
  showState: false,
  showRemark: false,
  showArrivalDate: false
}

const tableData = ref<TableRow[]>([])
const loading = ref(false)

const pagination = reactive({
  pageIndex: 1,
  pageSize: 30,
  total: 0
})

/**
 * 导出相关数据
 */
const exportFileName = ref('商品收发汇总表')
const exportDataList = computed(() => {
  return tableData.value.map(row => ({
    '商品名称': row.goodsData?.name || '',
    '仓库': row.warehouseData?.name || '',
    '商品编号': row.goodsData?.number || '',
    '规格型号': row.goodsData?.spce || '',
    '单位': row.unit || '',
    '期初-成本': row.state?.uct || 0,
    '期初-数量': row.state?.uns || 0,
    '期初-总成本': row.state?.bct || 0,
    '采购单-成本': row.buy?.uct || 0,
    '采购单-数量': row.buy?.uns || 0,
    '采购单-总成本': row.buy?.bct || 0,
    '采购退货单-成本': row.bre?.uct || 0,
    '采购退货单-数量': row.bre?.uns || 0,
    '采购退货单-总成本': row.bre?.bct || 0,
    '销售单-成本': row.sell?.uct || 0,
    '销售单-数量': row.sell?.uns || 0,
    '销售单-总成本': row.sell?.bct || 0,
    '销售退货单-成本': row.sre?.uct || 0,
    '销售退货单-数量': row.sre?.uns || 0,
    '销售退货单-总成本': row.sre?.bct || 0,
    '调拨单-出-成本': row.swapOut?.uct || 0,
    '调拨单-出-数量': row.swapOut?.uns || 0,
    '调拨单-出-总成本': row.swapOut?.bct || 0,
    '调拨单-入-成本': row.swapEnter?.uct || 0,
    '调拨单-入-数量': row.swapEnter?.uns || 0,
    '调拨单-入-总成本': row.swapEnter?.bct || 0,
    '其它入库单-成本': row.entry?.uct || 0,
    '其它入库单-数量': row.entry?.uns || 0,
    '其它入库单-总成本': row.entry?.bct || 0,
    '其它出库单-成本': row.extry?.uct || 0,
    '其它出库单-数量': row.extry?.uns || 0,
    '其它出库单-总成本': row.extry?.bct || 0,
    '汇总-成本': row.balance?.uct || 0,
    '汇总-数量': row.balance?.uns || 0,
    '汇总-总成本': row.balance?.bct || 0
  }))
})

async function loadData(page?: number) {
  if (page !== undefined) {
    pagination.pageIndex = page
  }

  loading.value = true

  try {
    const res = await WarehouseReportAPI.summaryList(buildSummaryParams())
    const { rows, total } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    tableData.value = rows as TableRow[]
    pagination.total = total
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    pagination.total = 0
    ElMessage.error(error instanceof Error ? error.message : '加载收发汇总失败')
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
    ElMessage.info('正在导出商品收发汇总表...')
    const blob = await WarehouseReportAPI.summaryExport(buildSummaryParams())
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
  loadData(1)
  ElMessage.success('数据已刷新')
}

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

/**
 * 格式化数字
 */
function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null) return '-'
  return value.toFixed(2)
}
</script>

<style scoped lang="scss">
.inventory-receipt-summary {
  height: 100%;
  display: flex;
  flex-direction: column;

  .layout {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

