<template>
  <div class="current-account area">
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

      <!-- 账户名称 -->
      <el-table-column 
        prop="name" 
        label="账户名称" 
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 单据类型 -->
      <el-table-column 
        prop="extension.type" 
        label="单据类型" 
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 所属组�?-->
      <el-table-column 
        prop="sourceData.frameData.name" 
        label="所属组织"
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 往来单�?-->
      <el-table-column 
        prop="current.name" 
        label="往来单位"
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 单据时间 -->
      <el-table-column 
        prop="sourceData.time" 
        label="单据时间" 
        align="center" 
        width="120px"
      ></el-table-column>

      <!-- 单据编号 -->
      <el-table-column 
        prop="sourceData.number" 
        label="单据编号" 
        align="center" 
        width="180px"
      ></el-table-column>

      <!-- 收入 -->
      <el-table-column 
        prop="in" 
        label="收入" 
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.in) }}
        </template>
      </el-table-column>

      <!-- 支出 -->
      <el-table-column 
        prop="out" 
        label="支出" 
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.out) }}
        </template>
      </el-table-column>

      <!-- 账户余额 -->
      <el-table-column 
        prop="balance" 
        label="账户余额" 
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.balance) }}
        </template>
      </el-table-column>

      <!-- 制单�?-->
      <el-table-column 
        prop="sourceData.userData.name" 
        label="制单人"
        align="center" 
        width="100px"
      ></el-table-column>

      <!-- 备注 -->
      <el-table-column 
        prop="sourceData.data" 
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
  cashBankStatementUsingGet,
  cashBankStatementOpenApiExportUsingGet
} from '@/apis/openapi-apifox/xianjinyinxingbaobiao'
import type {
  CashBankStatementUsingGetParams,
  CashBankStatementOpenApiExportUsingGetParams
} from '@/apis/openapi-apifox/types'
import { mapCashBankRow, unwrapPage, downloadExportBlob } from '@/utils/reportMappers'

/**
 * 类型定义
 */
interface FrameData {
  name: string
}

interface UserData {
  name: string
}

interface SourceData {
  frameData: FrameData
  time: string
  number: string
  userData: UserData
  data: string
}

interface Current {
  name: string
}

interface Extension {
  type: string
}

interface TableRow {
  key: string
  name: string
  extension: Extension
  sourceData: SourceData
  current: Current
  in: number
  out: number
  balance: number
  node?: TableRow[]  // 树形结构的子节点
}

/**
 * 搜索配置
 */
const searchConfig: GoodSearchConfig = {
  showGoods: false,
  showNumber: false,
  showSupplier: true,     // 显示供应�
  showCustomer: true,     // 显示客户
  showWarehouse: false,
  showAccount: true,      // 显示资金账户
  showBillDate: true,     // 显示单据日期范围
  showArrivalDate: false,
  showUser: true,         // 显示制单�
  showPeople: false,
  showExamine: false,
  showState: false,
  showRemark: false
}

/**
 * 响应式数据
 */
const searchForm = ref<SearchFormData>({
  customer: null,
  supplier: null,
  startTime: '',
  endTime: '',
  user: null,
  account: null
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
const exportFileName = ref('现金银行报表')
const exportDataList = computed(() => {
  const flattenData = (rows: TableRow[], level = 0): any[] => {
    const result: any[] = []
    rows.forEach(row => {
      result.push({
        '账户名称': level > 0 ? `${'  '.repeat(level)}${row.name}` : row.name,
        '单据类型': row.extension?.type || '',
        '所属组织': row.sourceData?.frameData?.name || '',
        '往来单位': row.current?.name || '',
        '单据时间': row.sourceData?.time || '',
        '单据编号': row.sourceData?.number || '',
        '收入': row.in || 0,
        '支出': row.out || 0,
        '账户余额': row.balance || 0,
        '制单人': row.sourceData?.userData?.name || '',
        '备注': row.sourceData?.data || ''
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

function buildSearchParams(): Partial<CashBankStatementUsingGetParams> {
  const params: Partial<CashBankStatementUsingGetParams> = {}
  const form = searchForm.value
  if (form.customer) params.customer = String(form.customer)
  if (form.supplier) params.supplier = String(form.supplier)
  if (form.startTime) params.startTime = String(form.startTime)
  if (form.endTime) params.endTime = String(form.endTime)
  if (form.user) params.user = String(form.user)
  if (form.account) params.account = String(form.account)
  return params
}

/**
 * 加载数据
 */
async function loadData(page?: number) {
  if (page !== undefined) {
    pagination.pageIndex = page
  }

  loading.value = true

  try {
    const params: CashBankStatementUsingGetParams = {
      pageIndex: pagination.pageIndex,
      pageSize: pagination.pageSize,
      ...buildSearchParams()
    }

    const res = await cashBankStatementUsingGet({ params })
    const { rows, total } = unwrapPage(res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string })
    tableData.value = rows.map((item, index) =>
      mapCashBankRow(item as Record<string, unknown>, index) as TableRow
    )
    pagination.total = total
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    pagination.total = 0
    ElMessage.error(error instanceof Error ? error.message : '加载现金银行报表失败')
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
    ElMessage.info('正在导出现金银行报表...')
    const params: CashBankStatementOpenApiExportUsingGetParams = {
      pageIndex: 1,
      pageSize: 99999,
      ...buildSearchParams()
    }
    const res = await cashBankStatementOpenApiExportUsingGet({ params })
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
.current-account {
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

