<template>
  <div class="sys area">
    <div class="operation-bar">
      <div class="operation-left">
        <el-popover
          placement="bottom-start"
          :width="400"
          trigger="click"
          v-model:visible="searchPopoverVisible"
          :teleported="false"
          :persistent="false"
        >
          <template #reference>
            <el-button class="search-btn">
              <el-icon><MoreFilled /></el-icon><span>筛选查询</span>
            </el-button>
          </template>
          <div class="search-popover">
            <div class="search-form">
              <div class="form-item">
                <el-input
                  v-model="searchForm.productName"
                  placeholder="请输入商品名称"
                  clearable
                />
              </div>
              <div class="form-item">
                <el-input
                  v-model="searchForm.productCode"
                  placeholder="请输入商品编号"
                  clearable
                />
              </div>
              <div class="form-item">
                <div class="date-range">
                  <el-date-picker
                    v-model="searchForm.orderStartDate"
                    type="date"
                    placeholder="开始日期"
                    style="width: 48%"
                    value-format="YYYY-MM-DD"
                  />
                  <span class="date-separator">至</span>
                  <el-date-picker
                    v-model="searchForm.orderEndDate"
                    type="date"
                    placeholder="结束日期"
                    style="width: 48%"
                    value-format="YYYY-MM-DD"
                  />
                </div>
              </div>
              <div class="form-actions">
                <el-button type="primary" @click="handleSearch" class="search-action-btn">
                  搜索
                </el-button>
                <el-button @click="handleResetSearch" class="reset-action-btn">重置</el-button>
              </div>
            </div>
          </div>
        </el-popover>
      </div>
      <div class="operation-right">
        <el-button type="primary" @click="handleExport" class="action-btn">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button type="info" @click="handleResetSearch" class="action-btn">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-divider class="custom-divider" />

    <div class="table-container">
      <el-table
        :data="filteredTableData"
        style="width: 100%"
        v-loading="loading"
        border
        class="grid-table"
      >
        <el-table-column prop="productName" label="商品名称" width="150" />
        <el-table-column prop="auxiliaryAttr" label="辅助属性" width="120" />
        <el-table-column prop="productCode" label="商品编号" width="120" />
        <el-table-column prop="specification" label="规格型号" width="120" />
        <el-table-column prop="unit" label="单位" width="80" align="center" />
        <el-table-column prop="quantity" label="数量" width="100" align="right" />
        <el-table-column prop="discount" label="折扣额" width="120" align="right">
          <template #default="scope">
            <span>{{ formatCurrency(scope.row.discount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="tax" label="税额" width="120" align="right">
          <template #default="scope">
            <span>{{ formatCurrency(scope.row.tax) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="totalWithTax" label="价税合计" width="120" align="right">
          <template #default="scope">
            <span class="total-highlight">{{ formatCurrency(scope.row.totalWithTax) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本" width="120" align="right">
          <template #default="scope">
            <span>{{ formatCurrency(scope.row.cost) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="totalCost" label="总成本" width="120" align="right">
          <template #default="scope">
            <span class="total-cost-highlight">{{ formatCurrency(scope.row.totalCost) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="grossProfit" label="毛利润" width="120" align="right">
          <template #default="scope">
            <span>{{ formatCurrency(scope.row.grossProfit) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="grossProfitMargin" label="毛利率" width="100" align="right">
          <template #default="scope">
            <span>{{ (scope.row.grossProfitMargin * 100).toFixed(2) }}%</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container pagination-left">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 30, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh, MoreFilled } from '@element-plus/icons-vue'
import { useClosePopoverOnLeave } from '@/composables/useClosePopoverOnLeave'

import {
  salesRankingTableUsingGet,
  salesRankingTableOpenApiExportUsingGet
} from '@/apis/report/sales/xiaoshoupaixingbiao'
import type {
  SalesRankingTableUsingGetParams,
  SalesRankingTableOpenApiExportUsingGetParams
} from '@/apis/report/sales/types'

// ================= 1. 类型定义 =================
interface SalesRankingRow {
  id?: number | string
  productName: string
  auxiliaryAttr: string
  productCode: string
  specification: string
  unit: string
  quantity: number
  discount: number
  tax: number
  totalWithTax: number
  cost: number
  totalCost: number
  grossProfit: number
  grossProfitMargin: number
}

interface SearchForm {
  productName: string
  productCode: string
  orderStartDate: string
  orderEndDate: string
}

// ================= 2. 搜索弹框 & 表单 =================
const searchPopoverVisible = ref(false)
useClosePopoverOnLeave(searchPopoverVisible)

const searchForm = reactive<SearchForm>({
  productName: '',
  productCode: '',
  orderStartDate: '',
  orderEndDate: ''
})

// ================= 3. 表格 & 分页状态
// =================
const tableData = ref<SalesRankingRow[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)

//  模板里还是用 :data="filteredTableData"，这里做一个简单映�
const filteredTableData = computed(() => tableData.value)

// ================= 4. 构建后端查询参数（命名适配�?=================
const buildSearchParams = (): Partial<SalesRankingTableUsingGetParams> => {
  const params: Partial<SalesRankingTableUsingGetParams> = {}

  // 商品名称 -> productName
  if (searchForm.productName) {
    params.productName = searchForm.productName
  }

  // 商品编号 -> productNumber
  if (searchForm.productCode) {
    params.productNumber = searchForm.productCode
  }

  // 单据开始日�?-> begintime
  if (searchForm.orderStartDate) {
    params.begintime = searchForm.orderStartDate
  }

  // 单据结束日期 -> endtime
  if (searchForm.orderEndDate) {
    params.endtime = searchForm.orderEndDate
  }

  return params
}

// ================= 5. 调接口获取数�?=================
const fetchTableData = async () => {
  loading.value = true
  try {
    const params: SalesRankingTableUsingGetParams = {
      pageIndex: currentPage.value,
      pageSize: pageSize.value,
      ...buildSearchParams()
    }

    const res = await salesRankingTableUsingGet({ params })
    const anyRes: any = res

    // 兼容 openapi-ts 可能生成的几种结构：
    // 1) { code, data: { data: { rows, total } } }
    // 2) { code, data: { rows, total } }
    // 3) 直接 { rows, total }
    const pageWrapper = anyRes?.data?.data ?? anyRes?.data ?? anyRes

    const list: any[] = pageWrapper?.rows ?? []
    const totalCount: number = pageWrapper?.total ?? 0

    // ======= 关键：rows -> 页面字段 映射（按你给的示例） =======
    tableData.value = list.map((item: any, index: number) => ({
      id: item.id ?? index,
      productName: item.productName ?? '',
      auxiliaryAttr: item.auxiliaryAttribute ?? '',
      productCode:
        item.productNumber !== undefined && item.productNumber !== null
          ? String(item.productNumber)
          : '',
      specification: item.specificationModel ?? '',
      unit: item.unit ?? '',
      quantity: Number(item.quantity ?? 0),
      discount: Number(item.discountAmount ?? 0),
      tax: Number(item.taxAmount ?? 0),
      totalWithTax: Number(item.totalAmountWithTax ?? 0),
      cost: Number(item.cost ?? 0),
      totalCost: Number(item.totalCost ?? 0),
      grossProfit: Number(item.grossProfit ?? 0),
      grossProfitMargin: Number(item.grossProfitMargin ?? 0)
    }))

    total.value = totalCount
  } catch (error: any) {
    console.error('获取销售排行表失败', error)
    ElMessage.error(error?.message || '获取销售排行表失败')
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// ================= 6. 搜索 / 重置 / 刷新 =================
const handleSearch = () => {
  searchPopoverVisible.value = false
  currentPage.value = 1
  fetchTableData()
  ElMessage.success('数据已刷新')
}

const handleResetSearch = () => {
  Object.assign(searchForm, {
    productName: '',
    productCode: '',
    orderStartDate: '',
    orderEndDate: ''
  })
  ElMessage.info('已重置搜索条件')
  currentPage.value = 1
  fetchTableData()
  ElMessage.success('数据已刷新')
}

const handleExport = async () => {
  try {
    ElMessage.info('正在导出数据...')

    const baseParams = buildSearchParams()
    const params: SalesRankingTableOpenApiExportUsingGetParams = {
      pageIndex: 1,
      pageSize: 99999, // 一般导出是所有满足条件的数据
      ...baseParams
    }

    const res = await salesRankingTableOpenApiExportUsingGet({ params })
    const anyRes: any = res

    let blob: Blob
    if (anyRes instanceof Blob) {
      blob = anyRes
    } else if (anyRes?.data instanceof Blob) {
      blob = anyRes.data
    } else {
      blob = new Blob([JSON.stringify(anyRes)], {
        type: 'application/octet-stream'
      })
    }

    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `销售排行表_${new Date().toISOString().split('T')[0]}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    ElMessage.success('数据已刷新')
  } catch (error: any) {
    console.error('导出销售排行表失败', error)
    ElMessage.error(error?.message || '导出销售排行表失败')
  }
}

// ================= 8. 工具函数 =================
const formatCurrency = (value: number | string | null | undefined) => {
  const num = Number(value) || 0
  return `¥${num.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`
}

// ================= 9. 分页（服务端分页�?=================
const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchTableData()
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
  fetchTableData()
}

// ================= 10. 初始化
onMounted(() => {
  fetchTableData()
})
</script>

<style scoped>
.sys.area {
  position: relative;
  padding: 16px;
  height: 100%; /* 减去padding */
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

/* 操作栏样�?*/
.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 0;
}

.operation-left,
.operation-right {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
}

.search-btn,
.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.more-actions .el-button {
  justify-content: flex-start;
  padding: 8px 16px;
}

/* 搜索弹框样式 */
.search-popover {
  padding: 0;
}

.search-form {
  padding: 16px;
}

.form-item {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-separator {
  color: #909399;
  font-size: 12px;
  width: 20px;
  text-align: center;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

.search-action-btn,
.reset-action-btn {
  min-width: 60px;
}

/* 分割线样�?*/
.custom-divider {
  margin: 8px 0;
  border-color: #e4e7ed;
}

/* 表格容器 - 占据剩余空间 */
.table-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0; /* 重要：防止flex item溢出 */
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

/* 表格样式 */
:deep(.el-table) {
  flex: 1;
}

:deep(.el-table .el-table__row) {
  cursor: pointer;
}

/* 网状表格样式 */
:deep(.grid-table) {
  border: 1px solid #ebeef5;
}

:deep(.grid-table .el-table__header-wrapper) {
  border-bottom: 1px solid #ebeef5;
}

:deep(.grid-table .el-table__cell) {
  border-right: 1px solid #ebeef5;
}

:deep(.grid-table .el-table__row) {
  border-bottom: 1px solid #ebeef5;
}

/* 高亮样式 */
/* .quantity-highlight {
  font-weight: bold;
  color: #409EFF;
}

.total-highlight {
  font-weight: bold;
  color: #67C23A;
}

.total-cost-highlight {
  font-weight: bold;
  color: #E6A23C;
} */

/* 分页容器样式 - 移动到左下角 */
.pagination-container {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  background: #fafafa;
  display: flex;
}

.pagination-left {
  justify-content: flex-start;
}

/* 响应式设�?*/
@media (max-width: 768px) {
  .sys.area {
    padding: 8px;
    height: 100%;
  }

  .operation-bar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .operation-left,
  .operation-right {
    justify-content: center;
  }

  .operation-left {
    border-bottom: 1px solid #e4e7ed;
    padding-bottom: 12px;
  }

  .search-popover {
    width: 280px !important;
  }

  :deep(.el-dialog) {
    width: 90% !important;
    max-width: 400px;
  }

  .pagination-container {
    justify-content: center;
  }
}

/* 美化滚动�?*/
:deep(.el-table__body-wrapper)::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

:deep(.el-table__body-wrapper)::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

:deep(.el-table__body-wrapper)::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

:deep(.el-table__body-wrapper)::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
