<template>
  <div class="debt-age-analysis area">
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
      <!-- 单位类型 -->
      <el-table-column 
        prop="mold" 
        label="单位类型" 
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 单位名称 -->
      <el-table-column 
        prop="name" 
        label="单位名称" 
        align="center" 
        width="160px"
      ></el-table-column>

      <!-- 单位编号 -->
      <el-table-column 
        prop="number" 
        label="单位编号" 
        align="center" 
        width="160px"
      ></el-table-column>

      <!-- 应收款余�?-->
      <el-table-column 
        prop="collection" 
        label="应收款余额"
        align="center" 
        width="120px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.collection) }}
        </template>
      </el-table-column>

      <!-- 应付款余�?-->
      <el-table-column 
        prop="payment" 
        label="应付款余额"
        align="center" 
        width="120px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.payment) }}
        </template>
      </el-table-column>

      <!-- 备注信息 -->
      <el-table-column 
        prop="data" 
        label="备注信息" 
        align="center" 
        width="160px"
      ></el-table-column>
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

    <!-- 底部统计信息 -->
    <div class="page-status">
      <span class="status-item">总应收款余额：{{ formatNumber(totalCollection) }}</span>
      <span class="status-item">总应付款余额：{{ formatNumber(totalPayment) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import GoodSearchForm from '@/components/goodSearchConpoent'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent'
import {
  unitArrearsReportFormUsingGet,
  unitArrearsReportFormOpenApiExportUsingGet
} from '@/apis/openapi-apifox/wanglaidanweiqiekuanbiao'
import type {
  UnitArrearsReportFormUsingGetParams,
  UnitArrearsReportFormOpenApiExportUsingGetParams
} from '@/apis/openapi-apifox/types'
import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'

function mapDebtAgeRow(item: Record<string, unknown>): TableRow {
  return {
    mold: String(item.type ?? ''),
    name: String(item.name ?? ''),
    number: String(item.number ?? ''),
    collection: Number(item.balanceCol) || 0,
    payment: Number(item.balancePay) || 0,
    data: String(item.data ?? '')
  }
}

function buildSearchParams(): Partial<UnitArrearsReportFormUsingGetParams> {
  const params: Partial<UnitArrearsReportFormUsingGetParams> = {}
  const form = searchForm.value
  if (form.name) params.name = String(form.name)
  if (form.number) params.number = String(form.number)
  if (form.data) params.data = String(form.data)
  if (form.mold && Array.isArray(form.mold) && form.mold.length) {
    params.type = String(form.mold[0])
  } else if (form.mold) {
    params.type = String(form.mold)
  }
  return params
}

/**
 * 类型定义
 */
interface TableRow {
  mold: string
  name: string
  number: string
  collection: number
  payment: number
  data: string
}

/**
 * 搜索配置
 */
const searchConfig: GoodSearchConfig = {
  showGoods: false,
  showNumber: false,
  showSupplier: false,
  showCustomer: false,
  showWarehouse: false,
  showAccount: false,
  showBillDate: false,
  showArrivalDate: false,
  showUser: false,
  showPeople: false,
  showExamine: false,
  showState: false,
  showRemark: false,
  customFields: [
    {
      key: 'name',
      type: 'input',
      label: '请输入单位名称'
    },
    {
      key: 'number',
      type: 'input',
      label: '请输入单位编号'
    },
    {
      key: 'mold',
      type: 'select',
      label: '单位类型',
      options: [
        { label: '客户', value: 'customer' },
        { label: '供应商', value: 'supplier' }
      ]
    },
    {
      key: 'data',
      type: 'input',
      label: '请输入备注信息'
    }
  ]
}

/**
 * 响应式数据
 */
const searchForm = ref<SearchFormData>({
  name: '',
  number: '',
  mold: [],
  data: ''
})

const tableData = ref<TableRow[]>([])
const loading = ref(false)

const pagination = reactive({
  pageIndex: 1,
  pageSize: 30,
  total: 0
})

/**
 * 计算总应收款余额
 */
const totalCollection = computed(() => {
  return tableData.value.reduce((sum, row) => sum + (row.collection || 0), 0)
})

/**
 * 计算总应付款余额
 */
const totalPayment = computed(() => {
  return tableData.value.reduce((sum, row) => sum + (row.payment || 0), 0)
})

/**
 * 导出相关数据
 */
const exportFileName = ref('往来单位欠款表')
const exportDataList = computed(() => {
  return tableData.value.map(row => ({
    '单位类型': row.mold === 'customer' ? '客户' : row.mold === 'supplier' ? '供应商': row.mold,
    '单位名称': row.name || '',
    '单位编号': row.number || '',
    '应收款余额': row.collection || 0,
    '应付款余额': row.payment || 0,
    '备注信息': row.data || ''
  }))
})

/**
 * 初始化
 */
onMounted(() => {
  loadData(1)
})

async function loadData(page?: number) {
  if (page !== undefined) {
    pagination.pageIndex = page
  }

  loading.value = true

  try {
    const params: UnitArrearsReportFormUsingGetParams = {
      pageIndex: pagination.pageIndex,
      pageSize: pagination.pageSize,
      ...buildSearchParams()
    }
    const res = await unitArrearsReportFormUsingGet({ params })
    const { rows, total } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    tableData.value = rows.map((item) => mapDebtAgeRow(item as Record<string, unknown>))
    pagination.total = total
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    pagination.total = 0
    ElMessage.error(error instanceof Error ? error.message : '加载往来单位欠款表失败')
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
    ElMessage.info('正在导出往来单位欠款表...')
    const params: UnitArrearsReportFormOpenApiExportUsingGetParams = {
      pageIndex: 1,
      pageSize: 99999,
      ...buildSearchParams()
    }
    const res = await unitArrearsReportFormOpenApiExportUsingGet({ params })
    downloadExportBlob(res, `${exportFileName.value}_${getCurrentDate()}.xlsx`)
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
.debt-age-analysis {
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

  .page-status {
    margin-top: 10px;
    padding: 10px;
    background-color: #f5f7fa;
    border-radius: 4px;
    display: flex;
    gap: 30px;
    justify-content: center;
    font-size: 14px;
    color: #606266;

    .status-item {
      font-weight: 500;
      
      &:first-child {
        color: #67c23a;
      }
      
      &:last-child {
        color: #e6a23c;
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

