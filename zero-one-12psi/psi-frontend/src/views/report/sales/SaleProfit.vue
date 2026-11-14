<template>
  <div class="sys area">
    <!-- 操作按钮 -->
    <div class="operation-bar">
      <div class="operation-left">
        <!-- 使用搜索组件 -->
        <GoodSearch
          :modelValue="searchFormData"
          :config="searchConfig"
          @update:modelValue="handleSearchFormUpdate"
          @search="handleGoodSearch"
          ref="goodSearchRef"
        />
      </div>

      <div class="operation-right">
        <el-button type="primary" @click="handleExport" class="action-btn">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button type="info" @click="handleRefresh" class="action-btn">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <el-divider class="custom-divider" />

    <!-- 表格区域 - 占据主要空间 -->
    <div class="table-container">
      <el-table
        :data="currentPageData"
        style="width: 100%"
        v-loading="loading"
        border
        class="grid-table"
      >
        <!-- 单据类型 -->
        <el-table-column prop="orderType" label="单据类型" width="100" align="center">
          <template #default="scope">
            {{ scope.row.orderType }}
          </template>
        </el-table-column>

        <!-- 所属组�?-->
        <el-table-column prop="orgName" label="所属组织" width="120" align="center" />

        <!-- 客户 -->
        <el-table-column prop="customerName" label="客户" width="150" />

        <!-- 单据时间 -->
        <el-table-column prop="orderDate" label="单据时间" width="120" align="center" />

        <!-- 单据编号 -->
        <el-table-column prop="orderNo" label="单据编号" width="150" />

        <!-- 商品名称列 -->
        <el-table-column v-if="showDetails" prop="productName" label="商品名称" width="150" />

        <!-- 辅助属�?- 明细显示 -->
        <el-table-column v-if="showDetails" prop="auxiliaryAttr" label="辅助属性" width="120" />

        <!-- 单位 - 明细显示 -->
        <el-table-column v-if="showDetails" prop="unit" label="单位" width="80" align="center" />

        <!-- 单价 - 明细显示 -->
        <el-table-column v-if="showDetails" prop="unitPrice" label="单价" width="100" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.unitPrice) }}
          </template>
        </el-table-column>

        <!-- 数量 - 明细显示 -->
        <el-table-column
          v-if="showDetails"
          prop="quantity"
          label="数量"
          width="100"
          align="right"
        />

        <!-- 折扣�?- 明细显示 -->
        <el-table-column
          v-if="showDetails"
          prop="discountAmount"
          label="折扣额" width="100"
          align="right"
        >
          <template #default="scope">
            {{ formatCurrency(scope.row.discountAmount) }}
          </template>
        </el-table-column>

        <!-- 金额 - 明细显示 -->
        <el-table-column v-if="showDetails" prop="amount" label="金额" width="120" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.amount) }}
          </template>
        </el-table-column>

        <!-- 税额 - 明细显示 -->
        <el-table-column v-if="showDetails" prop="taxAmount" label="税额" width="100" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.taxAmount) }}
          </template>
        </el-table-column>

        <!-- 价税合计 - 明细显示 -->
        <el-table-column
          v-if="showDetails"
          prop="totalWithTax"
          label="价税合计"
          width="120"
          align="right"
        >
          <template #default="scope">
            {{ formatCurrency(scope.row.totalWithTax) }}
          </template>
        </el-table-column>

        <!-- 以下为非明细列，始终显示 -->
        <!-- 单据金额 -->
        <el-table-column prop="orderAmount" label="单据金额" width="120" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.orderAmount) }}
          </template>
        </el-table-column>

        <!-- 优惠金额 -->
        <el-table-column prop="discountTotal" label="优惠金额" width="120" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.discountTotal) }}
          </template>
        </el-table-column>

        <!-- 实际金额 -->
        <el-table-column prop="actualAmount" label="实际金额" width="120" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.actualAmount) }}
          </template>
        </el-table-column>

        <!-- 成本 -->
        <el-table-column prop="cost" label="成本" width="120" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.cost) }}
          </template>
        </el-table-column>

        <!-- 毛利�?-->
        <el-table-column prop="grossProfit" label="毛利润" width="120" align="right">
          <template #default="scope">
            <span :class="getProfitClass(scope.row.grossProfit)">
              {{ formatCurrency(scope.row.grossProfit) }}
            </span>
          </template>
        </el-table-column>

        <!-- 毛利�?-->
        <el-table-column prop="grossProfitRate" label="毛利率" width="100" align="right">
          <template #default="scope">
            <span :class="getProfitClass(scope.row.grossProfitRate)">
              {{ formatPercentage(scope.row.grossProfitRate) }}
            </span>
          </template>
        </el-table-column>

        <!-- 单据费用 -->
        <el-table-column prop="orderFee" label="单据费用" width="120" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.orderFee) }}
          </template>
        </el-table-column>

        <!-- 净利润 -->
        <el-table-column prop="netProfit" label="净利润" width="120" align="right">
          <template #default="scope">
            <span :class="getProfitClass(scope.row.netProfit)">
              {{ formatCurrency(scope.row.netProfit) }}
            </span>
          </template>
        </el-table-column>

        <!-- 净利率 -->
        <el-table-column prop="netProfitRate" label="净利率" width="100" align="right">
          <template #default="scope">
            <span :class="getProfitClass(scope.row.netProfitRate)">
              {{ formatPercentage(scope.row.netProfitRate) }}
            </span>
          </template>
        </el-table-column>

        <!-- 核销金额 -->
        <el-table-column prop="verificationAmount" label="核销金额" width="120" align="right">
          <template #default="scope">
            {{ formatCurrency(scope.row.verificationAmount) }}
          </template>
        </el-table-column>

        <!-- 核销状�?-->
        <el-table-column prop="verificationStatus" label="核销状态" width="100" align="center">
          <template #default="scope">
            {{ scope.row.verificationStatus }}
          </template>
        </el-table-column>

        <!-- 制单�?-->
        <el-table-column prop="createdBy" label="制单人" width="100" align="center" />

        <!-- 关联人员 -->
        <el-table-column prop="relatedPerson" label="关联人员" width="100" align="center" />

        <!-- 备注信息 -->
        <el-table-column prop="remark" label="备注信息" min-width="150" />
      </el-table>

      <!-- 分页区域 -->
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
import { Download, Refresh } from '@element-plus/icons-vue'
import GoodSearch from '@/components/goodSearchConpoent/GoodSearchForm.vue'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent/type'
import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'
import {
  salesProfitUsingGet,
  salesProfitOpenApiExportUsingGet
} from '@/apis/openapi-apifox/xiaoshoulirunbiao'
import type { SalesProfitUsingGetParams } from '@/apis/openapi-apifox/types'

// 搜索组件引用
const goodSearchRef = ref()

// 是否显示明细
const showDetails = ref(false)

const mapOrderType = (type: unknown) => {
  const n = Number(type)
  if (n === 0) return '销售单'
  if (n === 1) return '销售退货单'
  return String(type ?? '')
}

const mapSalesProfitRow = (item: Record<string, unknown>, index: number) => {
  const amount = Number(item.total) || 0
  const discountAmount = Number(item.dsc) || 0
  const totalWithTax = Number(item.tpt) || 0
  return {
    id: index + 1,
    orderType: mapOrderType(item.type),
    orgName: String(item.frame ?? ''),
    customerName: String(item.customer ?? ''),
    orderDate: item.time ? String(item.time).slice(0, 10) : '',
    orderNo: String(item.number ?? ''),
    productName: String(item.name ?? ''),
    auxiliaryAttr: String(item.attr ?? ''),
    unit: String(item.unit ?? ''),
    unitPrice: Number(item.price) || 0,
    quantity: Number(item.nums) || 0,
    discountAmount,
    amount,
    taxAmount: Number(item.tat) || 0,
    totalWithTax,
    orderAmount: totalWithTax,
    discountTotal: discountAmount,
    actualAmount: totalWithTax - discountAmount,
    cost: 0,
    grossProfit: 0,
    grossProfitRate: 0,
    orderFee: 0,
    netProfit: 0,
    netProfitRate: 0,
    verificationAmount: 0,
    verificationStatus: '',
    createdBy: String(item.user ?? ''),
    relatedPerson: String(item.people ?? ''),
    remark: String(item.data ?? '')
  }
}

const buildApiParams = (): SalesProfitUsingGetParams => {
  const params: SalesProfitUsingGetParams = {
    pageIndex: 1,
    pageSize: 99999,
    data: searchFormData.showDetails || '隐藏明细'
  }
  if (searchFormData.customer) params.customer = String(searchFormData.customer)
  if (searchFormData.number) params.number = String(searchFormData.number)
  if (searchFormData.startTime) params.beginTime = String(searchFormData.startTime)
  if (searchFormData.endTime) params.leftTime = String(searchFormData.endTime)
  if (searchFormData.user) params.user = String(searchFormData.user)
  if (searchFormData.people) params.people = String(searchFormData.people)
  if (searchFormData.orderType === '销售单') params.type = '0'
  if (searchFormData.orderType === '销售退货单') params.type = '1'
  return params
}

async function loadData() {
  loading.value = true
  try {
    const res = await salesProfitUsingGet({ params: buildApiParams() })
    const { rows } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    const mapped = rows.map((r, i) => mapSalesProfitRow(r as Record<string, unknown>, i))
    originalTableData.value = mapped
    currentTableData.value = JSON.parse(JSON.stringify(mapped))
    currentPage.value = 1
  } catch (error: unknown) {
    originalTableData.value = []
    currentTableData.value = []
    ElMessage.error(error instanceof Error ? error.message : '加载销售利润表失败')
  } finally {
    loading.value = false
  }
}

const originalTableData = ref<any[]>([])

// 当前显示的表格数据
const currentTableData = ref<any[]>([])

// 搜索表单数据
const searchFormData = reactive<SearchFormData>({
  customer: null,
  number: '',
  startTime: '',
  endTime: '',
  user: null,
  people: null,
  orderType: '',
  showDetails: '隐藏明细'
})

//  搜索配置 - 调整为销售利润表的需�
const searchConfig = reactive<GoodSearchConfig>({
  showGoods: false,
  showNumber: true,
  showSupplier: false,
  showCustomer: true,
  showPeople: true,
  showBillDate: true,
  showArrivalDate: false,
  showUser: true,
  showExamine: false,
  showState: false,
  showRemark: false,
  inline: true,
  customFields: [
    {
      key: 'orderType',
      type: 'select',
      label: '单据类型',
      options: [
        { label: '全部', value: '' },
        { label: '销售单', value: '销售单' },
        { label: '销售退货单', value: '销售退货单' }
      ]
    },
    {
      key: 'showDetails',
      type: 'select',
      label: '显示明细',
      options: [
        { label: '隐藏明细', value: '隐藏明细' },
        { label: '显示明细', value: '显示明细' }
      ]
    }
  ]
})

// 处理搜索表单更新
const handleSearchFormUpdate = (newValue: SearchFormData) => {
  Object.assign(searchFormData, newValue)
  // 更新显示明细状�
  showDetails.value = newValue.showDetails === '显示明细'
}

// 处理搜索组件的搜索事件
const handleGoodSearch = (formData: SearchFormData) => {
  Object.assign(searchFormData, formData)
  showDetails.value = formData.showDetails === '显示明细'
  loadData()
  ElMessage.success('数据已刷新')
}

// 应用搜索过滤
const applySearchFilters = (formData: SearchFormData) => {
  let filteredData = JSON.parse(JSON.stringify(originalTableData.value))

  // 根据搜索条件过滤数据
  filteredData = filteredData.filter((item: any) => {
    // 过滤客户
    if (formData.customer && !item.customerName.includes(formData.customer as string)) {
      return false
    }

    // 过滤单据编号
    if (formData.number && !item.orderNo.includes(formData.number)) {
      return false
    }

    // 过滤单据类型
    if (formData.orderType && item.orderType !== formData.orderType) {
      return false
    }

    // 过滤单据日期范围
    if (formData.startTime || formData.endTime) {
      const orderDate = new Date(item.orderDate)
      const startDate = formData.startTime ? new Date(formData.startTime) : null
      const endDate = formData.endTime ? new Date(formData.endTime) : null

      if (startDate && orderDate < startDate) return false
      if (endDate && orderDate > endDate) return false
    }

    // 过滤制单人
    if (formData.user && !item.createdBy.includes(formData.user as string)) {
      return false
    }

    // 过滤关联人员
    if (formData.people && !item.relatedPerson.includes(formData.people as string)) {
      return false
    }

    return true
  })

  // 更新当前显示的数据
  currentTableData.value = filteredData
  currentPage.value = 1 // 重置到第一页
}

// 刷新功能
const handleRefresh = () => {
  if (goodSearchRef.value) {
    goodSearchRef.value.resetForm()
  }
  Object.assign(searchFormData, {
    customer: null,
    number: '',
    startTime: '',
    endTime: '',
    user: null,
    people: null,
    orderType: '',
    showDetails: '隐藏明细'
  })
  showDetails.value = false
  loadData()
  ElMessage.success('数据已刷新')
}

const handleExport = async () => {
  try {
    const res = await salesProfitOpenApiExportUsingGet({ params: buildApiParams() })
    downloadExportBlob(res, `销售利润表_${new Date().toISOString().split('T')[0]}.xlsx`)
    ElMessage.success('数据已刷新')
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  }
}

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)

//  计算总数据条�
const total = computed(() => {
  return currentTableData.value.length
})

//  当前页数�
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return currentTableData.value.slice(start, end)
})

// 分页处理
const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

//  格式化货�
const formatCurrency = (value: number) => {
  return `¥${value.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,')}`
}

// 格式化百分比
const formatPercentage = (value: number) => {
  return `${(value * 100).toFixed(2)}%`
}

//  获取利润样式�
const getProfitClass = (value: number) => {
  if (value > 0) return 'profit-positive'
  if (value < 0) return 'profit-negative'
  return ''
}

// 初始化
onMounted(() => {
  loadData()
})
</script>

<style scoped>
/* 样式保持不变 */
.sys.area {
  position: relative;
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

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

.custom-divider {
  margin: 8px 0;
  border-color: #e4e7ed;
}

.table-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.pagination-container {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  background: #fafafa;
  display: flex;
}

.pagination-left {
  justify-content: flex-start;
}

:deep(.el-table) {
  flex: 1;
}

/* 利润样式 */
/* .profit-positive {
  color: #f56c6c;
  font-weight: 600;
}

.profit-negative {
  color: #67c23a;
  font-weight: 600;
} */
</style>
