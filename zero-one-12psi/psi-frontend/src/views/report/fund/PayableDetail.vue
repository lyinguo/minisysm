<template>
  <div class="payable-detail area">
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
      :tree-props="{ children: 'node' }"
      row-key="key"
      height="calc(100% - 90px)"
      border
      v-loading="loading"
    >
      <!-- 空列 -->
      <el-table-column align="center" width="44px"></el-table-column>

      <!-- 供应�?-->
      <el-table-column 
        prop="name" 
        label="供应商"
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 单据类型 -->
      <el-table-column 
        prop="bill" 
        label="单据类型" 
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 所属组�?-->
      <el-table-column 
        prop="frameData.name" 
        label="所属组织"
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 单据时间 -->
      <el-table-column 
        prop="time" 
        label="单据时间" 
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 单据编号 -->
      <el-table-column 
        prop="number" 
        label="单据编号" 
        align="center" 
        width="180px"
      ></el-table-column>

      <!-- 增加应付�?-->
      <el-table-column 
        prop="cw" 
        label="增加应付款"
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.cw) }}
        </template>
      </el-table-column>

      <!-- 增加预付�?-->
      <el-table-column 
        prop="pia" 
        label="增加预付款"
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.pia) }}
        </template>
      </el-table-column>

      <!-- 应付款余�?-->
      <el-table-column 
        prop="balance" 
        label="应付款余额"
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.balance) }}
        </template>
      </el-table-column>

      <!-- 备注 -->
      <el-table-column 
        prop="data" 
        label="备注" 
        align="center" 
        width="200px"
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import GoodSearchForm from '@/components/goodSearchConpoent'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent'
import {
  detailedAccountPayableStatementQueryUsingGet,
  detailedAccountPayableStatementOpenApiExportUsingGet
} from '@/apis/openapi-apifox/yingfukuanmingxibiao'
import type {
  DetailedAccountPayableStatementQueryUsingGetParams,
  DetailedAccountPayableStatementOpenApiExportUsingGetParams
} from '@/apis/openapi-apifox/types'
import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'

function mapPayableRow(item: Record<string, unknown>, index: number): TableRow {
  return {
    key: String(item.documentNumber ?? index),
    name: String(item.supplier ?? ''),
    bill: String(item.documentType ?? ''),
    frameData: { name: String(item.frame ?? '') },
    time: item.dateTime ? String(item.dateTime).slice(0, 10) : '',
    number: String(item.documentNumber ?? ''),
    cw: Number(item.accountsPayableIncrease) || 0,
    pia: Number(item.advancePaymentIncrease) || 0,
    balance: Number(item.accountsPayableBalance) || 0,
    data: String(item.remark ?? '')
  }
}

function buildSearchParams(): Partial<DetailedAccountPayableStatementQueryUsingGetParams> {
  const params: Partial<DetailedAccountPayableStatementQueryUsingGetParams> = {}
  const form = searchForm.value
  if (form.supplier) params.supplier = String(form.supplier)
  if (form.startTime) params.startTime = String(form.startTime)
  if (form.endTime) params.endTime = String(form.endTime)
  if (form.type !== undefined && form.type !== null && form.type !== '') {
    params.supplierType = String(form.type)
  }
  return params
}

/**
 * 类型定义
 */
interface FrameData {
  name: string
}

interface TableRow {
  key: string
  name: string
  bill: string
  frameData: FrameData
  time: string
  number: string
  cw: number
  pia: number
  balance: number
  data: string
  node?: TableRow[]  // 树形结构的子节点
}

/**
 * 搜索配置
 */
const searchConfig: GoodSearchConfig = {
  showGoods: false,
  showNumber: false,
  showSupplier: true,     // 显示供应�
  showCustomer: false,
  showWarehouse: false,
  showAccount: false,
  showBillDate: true,     // 显示单据日期范围
  showArrivalDate: false,
  showUser: false,
  showPeople: false,
  showExamine: false,
  showState: false,
  showRemark: false,
  customFields: [
    {
      key: 'type',
      type: 'select',
      label: '数据类型',
      options: [
        { label: '全部供应商', value: 0 },
        { label: '欠款供应商', value: 1 }
      ]
    }
  ]
}

/**
 * 响应式数据
 */
const searchForm = ref<SearchFormData>({
  supplier: null,
  type: 0,
  startTime: '',
  endTime: ''
})

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
const exportFileName = ref('应付款明细表')
const exportDataList = computed(() => {
  const flattenData = (rows: TableRow[], level = 0): any[] => {
    const result: any[] = []
    rows.forEach(row => {
      result.push({
        '供应商': level > 0 ? `${'  '.repeat(level)}${row.name}` : row.name,
        '单据类型': row.bill || '',
        '所属组织': row.frameData?.name || '',
        '单据时间': row.time || '',
        '单据编号': row.number || '',
        '增加应付款': row.cw || 0,
        '增加预付款': row.pia || 0,
        '应付款余额': row.balance || 0,
        '备注': row.data || ''
      })
      if (row.node && row.node.length > 0) {
        result.push(...flattenData(row.node, level + 1))
      }
    })
    return result
  }
  return flattenData(tableData.value)
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
    const params: DetailedAccountPayableStatementQueryUsingGetParams = {
      pageIndex: pagination.pageIndex,
      pageSize: pagination.pageSize,
      ...buildSearchParams()
    }
    const res = await detailedAccountPayableStatementQueryUsingGet({ params })
    const { rows, total } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    tableData.value = rows.map((item, index) =>
      mapPayableRow(item as Record<string, unknown>, index)
    )
    pagination.total = total
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    pagination.total = 0
    ElMessage.error(error instanceof Error ? error.message : '加载应付款明细失败')
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
    ElMessage.info('正在导出应付款明细表...')
    const params: DetailedAccountPayableStatementOpenApiExportUsingGetParams = {
      pageIndex: 1,
      pageSize: 99999,
      ...buildSearchParams()
    }
    const res = await detailedAccountPayableStatementOpenApiExportUsingGet({ params })
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
  if (value === undefined || value === null || value === 0) return '-'
  return value.toFixed(2)
}
</script>

<style scoped lang="scss">
.payable-detail {
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

  // 树形表格样式 - 二级行背景色
  :deep(.el-table__row--level-1) {
    background: #fcfcfc;
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

