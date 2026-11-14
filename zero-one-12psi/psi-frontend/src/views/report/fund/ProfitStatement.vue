<template>
  <div class="profit-statement area">
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
      height="calc(100% - 60px)"
      border
      v-loading="loading"
    >
      <!-- 序号 -->
      <el-table-column 
        type="index" 
        align="center" 
        width="50px"
      ></el-table-column>

      <!-- 项目 -->
      <el-table-column 
        prop="name" 
        label="项目" 
        width="200px"
      ></el-table-column>

      <!-- 金额 -->
      <el-table-column 
        prop="money" 
        label="金额" 
        align="center" 
        width="120px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.money) }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import GoodSearchForm from '@/components/goodSearchConpoent'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent'
import { profitUsingGet, profitOpenApiExportUsingGet } from '@/apis/openapi-apifox/lirunbiao'
import type {
  ProfitUsingGetParams,
  ProfitOpenApiExportUsingGetParams
} from '@/apis/openapi-apifox/types'
import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'

function mapProfitRow(item: Record<string, unknown>): TableRow {
  const amount = item.amount
  const money =
    typeof amount === 'number' ? amount : parseFloat(String(amount ?? '0')) || 0
  return {
    name: String(item.projectName ?? ''),
    money
  }
}

function buildSearchParams(): Partial<ProfitUsingGetParams> {
  const params: Partial<ProfitUsingGetParams> = {}
  const form = searchForm.value
  if (form.startTime) params.startTime = String(form.startTime)
  if (form.endTime) params.endTime = String(form.endTime)
  return params
}

/**
 * 类型定义
 */
interface TableRow {
  name: string
  money: number
}

/**
 * 搜索配置 - 只显示日期范�? */
const searchConfig: GoodSearchConfig = {
  showGoods: false,
  showNumber: false,
  showSupplier: false,
  showCustomer: false,
  showWarehouse: false,
  showAccount: false,
  showBillDate: true,      // 只显示单据日期范�
  showArrivalDate: false,
  showUser: false,
  showPeople: false,
  showExamine: false,
  showState: false,
  showRemark: false
}

/**
 * 响应式数据
 */
const searchForm = ref<SearchFormData>({
  startTime: '',
  endTime: ''
})

const tableData = ref<TableRow[]>([])
const loading = ref(false)

/**
 * 导出相关数据
 */
const exportFileName = ref('利润表')
const exportDataList = computed(() => {
  return tableData.value.map(row => ({
    '项目': row.name || '',
    '金额': row.money || 0
  }))
})

/**
 * 初始化
 */
onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true

  try {
    const params: ProfitUsingGetParams = {
      pageIndex: 1,
      pageSize: 9999,
      ...buildSearchParams()
    }
    const res = await profitUsingGet({ params })
    const { rows } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    tableData.value = rows.map((item) => mapProfitRow(item as Record<string, unknown>))
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    ElMessage.error(error instanceof Error ? error.message : '加载利润表失败')
  } finally {
    loading.value = false
  }
}

/**
 * 处理搜索
 */
function handleSearch(formData: SearchFormData) {
  searchForm.value = formData
  loadData()
}

/**
 * 导出数据
 */
async function handleExport() {
  try {
    ElMessage.info('正在导出利润�?..')
    const params: ProfitOpenApiExportUsingGetParams = {
      pageIndex: 1,
      pageSize: 99999,
      ...buildSearchParams()
    }
    const res = await profitOpenApiExportUsingGet({ params })
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
  loadData()
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
.profit-statement {
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
</style>

