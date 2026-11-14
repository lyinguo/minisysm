<template>
  <div class="customer-statement area">
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
      ref="tableRef"
      :data="tableData"
      :tree-props="{ children: 'node' }"
      row-key="key"
      height="calc(100% - 60px)"
      border
      v-loading="loading"
    >
      <!-- 明细模式的空�?-->
      <el-table-column v-if="showDetail" align="center" width="44px"></el-table-column>

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

      <!-- 明细模式才显示的�?-->
      <template v-if="showDetail">
        <!-- 名称 -->
        <el-table-column 
          prop="detail.name" 
          label="名称" 
          align="center" 
          width="120px"
        ></el-table-column>

        <!-- 属�?-->
        <el-table-column 
          prop="detail.attr" 
          label="属性"
          align="center" 
          width="120px"
        ></el-table-column>

        <!-- 单位 -->
        <el-table-column 
          prop="detail.unit" 
          label="单位" 
          align="center" 
          width="100px"
        ></el-table-column>

        <!-- 单价 -->
        <el-table-column 
          prop="detail.price" 
          label="单价" 
          align="center" 
          width="100px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.detail?.price) }}
          </template>
        </el-table-column>

        <!-- 数量 -->
        <el-table-column 
          prop="detail.nums" 
          label="数量" 
          align="center" 
          width="100px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.detail?.nums) }}
          </template>
        </el-table-column>

        <!-- 折扣�?-->
        <el-table-column 
          prop="detail.dsc" 
          label="折扣额"
          align="center" 
          width="100px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.detail?.dsc) }}
          </template>
        </el-table-column>

        <!-- 金额 -->
        <el-table-column 
          prop="detail.total" 
          label="金额" 
          align="center" 
          width="100px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.detail?.total) }}
          </template>
        </el-table-column>

        <!-- 税额 -->
        <el-table-column 
          prop="detail.tat" 
          label="税额" 
          align="center" 
          width="100px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.detail?.tat) }}
          </template>
        </el-table-column>

        <!-- 价税合计 -->
        <el-table-column 
          prop="detail.tpt" 
          label="价税合计" 
          align="center" 
          width="100px"
        >
          <template #default="{ row }">
            {{ formatNumber(row.detail?.tpt) }}
          </template>
        </el-table-column>
      </template>

      <!-- 单据金额 -->
      <el-table-column 
        prop="total" 
        label="单据金额" 
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.total) }}
        </template>
      </el-table-column>

      <!-- 优惠金额 -->
      <el-table-column 
        prop="discount" 
        label="优惠金额" 
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.discount) }}
        </template>
      </el-table-column>

      <!-- 应收金额 -->
      <el-table-column 
        prop="actual" 
        label="应收金额" 
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.actual) }}
        </template>
      </el-table-column>

      <!-- 实收金额 -->
      <el-table-column 
        prop="money" 
        label="实收金额" 
        align="center" 
        width="100px"
      >
        <template #default="{ row }">
          {{ formatNumber(row.money) }}
        </template>
      </el-table-column>

      <!-- 应收款余�?-->
      <el-table-column 
        prop="balance" 
        label="应收款余额"
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import type { ElTable } from 'element-plus'
import GoodSearchForm from '@/components/goodSearchConpoent'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent'
import {
  customerStatementUsingGet,
  customerStatementOpenApiExportUsingGet
} from '@/apis/openapi-apifox/kehuduizhangdan'
import type {
  CustomerStatementUsingGetParams,
  CustomerStatementOpenApiExportUsingGetParams
} from '@/apis/openapi-apifox/types'
import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'

function mapCustomerStatementRow(item: Record<string, unknown>, index: number): TableRow {
  const details = Array.isArray(item.details) ? item.details : []
  const node: TableRow[] = details.map((d: Record<string, unknown>, i: number) => {
    const price = Number(d.price) || 0
    const nums = Number(d.nums) || 0
    return {
      key: `${index}_${i}`,
      bill: String(item.tableType ?? ''),
      frameData: { name: String(item.frame ?? '') },
      time: item.time ? String(item.time).slice(0, 10) : '',
      number: String(item.number ?? ''),
      detail: {
        name: String(d.goods ?? ''),
        attr: '',
        unit: '',
        price,
        nums,
        dsc: 0,
        total: price * nums,
        tat: 0,
        tpt: price * nums
      },
      total: Number(item.total) || 0,
      discount: Number(item.discountAmount) || 0,
      actual: Number(item.actual) || 0,
      money: Number(item.money) || 0,
      balance: Number(item.actual2) || 0,
      data: String(item.data ?? '')
    }
  })
  return {
    key: String(item.number ?? index),
    bill: String(item.tableType ?? ''),
    frameData: { name: String(item.frame ?? '') },
    time: item.time ? String(item.time).slice(0, 10) : '',
    number: String(item.number ?? ''),
    total: Number(item.total) || 0,
    discount: Number(item.discountAmount) || 0,
    actual: Number(item.actual) || 0,
    money: Number(item.money) || 0,
    balance: Number(item.actual2) || 0,
    data: String(item.data ?? ''),
    node: node.length > 0 ? node : undefined
  }
}

function buildSearchParams(): Partial<CustomerStatementUsingGetParams> {
  const params: Partial<CustomerStatementUsingGetParams> = {}
  const form = searchForm.value
  if (form.customer) params.name = String(form.customer)
  if (form.startTime) params.beginTime = String(form.startTime)
  if (form.endTime) params.endTime = String(form.endTime)
  params.hideOrShowDetail = form.type === 1
  return params
}

/**
 * 类型定义
 */
interface FrameData {
  name: string
}

interface DetailData {
  name: string
  attr: string
  unit: string
  price: number
  nums: number
  dsc: number
  total: number
  tat: number
  tpt: number
}

interface TableRow {
  key: string
  bill: string
  frameData: FrameData
  time: string
  number: string
  detail?: DetailData
  total: number
  discount: number
  actual: number
  money: number
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
  showSupplier: false,
  showCustomer: true,     // 显示客户（必选）
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
      label: '显示明细',
      options: [
        { label: '隐藏明细', value: 0 },
        { label: '显示明细', value: 1 }
      ]
    }
  ]
}

/**
 * 响应式数据
 */
const searchForm = ref<SearchFormData>({
  customer: null,
  type: 0,
  startTime: '',
  endTime: ''
})

const tableData = ref<TableRow[]>([])
const loading = ref(false)
const tableRef = ref<InstanceType<typeof ElTable>>()

/**
 * 是否显示明细
 */
const showDetail = computed(() => searchForm.value.type === 1)

/**
 * 导出相关数据
 */
const exportFileName = ref('客户对账单')

/**
 * 初始化
 */
onMounted(() => {
  // 客户对账单需要先选择客户才能查询
  // 所以初始化时不自动加载数据
})

async function loadData() {
  if (!searchForm.value.customer) {
    ElMessage.warning('请选择客户后搜索')
    return
  }

  loading.value = true

  try {
    const params: CustomerStatementUsingGetParams = {
      pageIndex: 1,
      pageSize: 9999,
      ...buildSearchParams()
    }
    const res = await customerStatementUsingGet({ params })
    const { rows } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    tableData.value = rows.map((item, index) =>
      mapCustomerStatementRow(item as Record<string, unknown>, index)
    )
    await nextTick()
    tableRef.value?.doLayout()
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    ElMessage.error(error instanceof Error ? error.message : '加载客户对账单失败')
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
  if (!searchForm.value.customer) {
    ElMessage.warning('请选择客户后导出')
    return
  }
  try {
    ElMessage.info('正在导出客户对账�?..')
    const params: CustomerStatementOpenApiExportUsingGetParams = {
      pageIndex: 1,
      pageSize: 99999,
      ...buildSearchParams()
    }
    const res = await customerStatementOpenApiExportUsingGet({ params })
    downloadExportBlob(res, `${exportFileName.value}_${getCurrentDate()}.xlsx`)
    ElMessage.success('数据已刷新')
  } catch (error: unknown) {
    console.error('导出失败:', error)
    ElMessage.error(error instanceof Error ? error.message : '导出失败，请稍后重试')
  }
}

/**
 * 扁平化表格数据用于导�? */
function flattenTableData(rows: TableRow[]): any[] {
  const result: any[] = []
  
  rows.forEach(row => {
    if (showDetail.value && row.node && row.node.length > 0) {
      // 有明细的情况
      row.node.forEach(detail => {
        result.push({
          '单据类型': row.bill,
          '所属组织': row.frameData?.name || '',
          '单据时间': row.time,
          '单据编号': row.number,
          '商品名称': detail.detail?.name || '',
          '属性': detail.detail?.attr || '',
          '单位': detail.detail?.unit || '',
          '单价': detail.detail?.price || 0,
          '数量': detail.detail?.nums || 0,
          '折扣额': detail.detail?.dsc || 0,
          '金额': detail.detail?.total || 0,
          '税额': detail.detail?.tat || 0,
          '价税合计': detail.detail?.tpt || 0,
          '单据金额': row.total || 0,
          '优惠金额': row.discount || 0,
          '应收金额': row.actual || 0,
          '实收金额': row.money || 0,
          '应收款余额': row.balance || 0,
          '备注': row.data || ''
        })
      })
    } else {
      // 无明细的情况
      result.push({
        '单据类型': row.bill,
        '所属组织': row.frameData?.name || '',
        '单据时间': row.time,
        '单据编号': row.number,
        '单据金额': row.total || 0,
        '优惠金额': row.discount || 0,
        '应收金额': row.actual || 0,
        '实收金额': row.money || 0,
        '应收款余额': row.balance || 0,
        '备注': row.data || ''
      })
    }
  })
  
  return result
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
  if (value === undefined || value === null || value === 0) return '-'
  return value.toFixed(2)
}
</script>

<style scoped lang="scss">
.customer-statement {
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

