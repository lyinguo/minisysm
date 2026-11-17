<template>
  <div class="sys area">
    <!-- 操作栏 -->
    <div class="operation-bar">
      <div class="operation-left">
        <!-- 搜索条件 -->
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

    <!-- 报表数据 -->
    <div class="table-container">
      <el-table
        v-if="tableAlive"
        :data="currentPageData"
        style="width: 100%"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        v-loading="loading"
        :default-expand-all="false"
        border
        class="grid-table"
      >
        <!-- 按商品分组 -->
        <template v-if="isProductSort">
          <!-- 商品名称 -->
          <el-table-column prop="productName" label="商品名称" width="150">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.productName }}
              </span>
            </template>
          </el-table-column>

          <!-- 辅助属性 -->
          <el-table-column prop="auxiliaryAttr" label="辅助属性" width="120">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.auxiliaryAttr }}
              </span>
            </template>
          </el-table-column>

          <!-- 仓库 -->
          <el-table-column prop="warehouse" label="仓库" width="120">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.warehouse }}
              </span>
            </template>
          </el-table-column>

          <!-- 所属组织 -->
          <el-table-column prop="orgName" label="所属组织" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getOrgSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orgName }}
              </span>
            </template>
          </el-table-column>

          <!-- 客户 -->
          <el-table-column prop="customerName" label="客户" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getCustomerSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.customerName }}
              </span>
            </template>
          </el-table-column>

          <!-- 单据时间 -->
          <el-table-column prop="orderDate" label="单据时间" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orderDate }}
              </span>
            </template>
          </el-table-column>

          <!-- 单据编号 -->
          <el-table-column prop="orderNo" label="单据编号" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getOrderNoSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orderNo }}
              </span>
            </template>
          </el-table-column>

          <!-- 单位 -->
          <el-table-column prop="unit" label="单位" width="80" align="center">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.unit }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <!-- 单价 -->
          <el-table-column prop="unitPrice" label="单价" width="100" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getAverageUnitPrice(scope.row) }}
              </span>
              <span v-else>
                {{ calculateUnitPrice(scope.row) }}
              </span>
            </template>
          </el-table-column>

          <!-- 数量 -->
          <el-table-column prop="quantity" label="数量" width="100" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.quantity }}
              </span>
            </template>
          </el-table-column>

          <!-- 金额 -->
          <el-table-column prop="amount" label="金额" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.amount }}
              </span>
            </template>
          </el-table-column>

          <!-- 出库状态 -->
          <el-table-column prop="storageStatus" label="出库状态" width="100" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getStorageStatusSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.storageStatus }}
              </span>
            </template>
          </el-table-column>

          <!-- 未出库数量 -->
          <el-table-column prop="unstockedQuantity" label="未出库数量" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedQuantity }}
              </span>
            </template>
          </el-table-column>

          <!-- 未出库金额 -->
          <el-table-column prop="unstockedAmount" label="未出库金额" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedAmount }}
              </span>
            </template>
          </el-table-column>

          <!-- 到货日期 -->
          <el-table-column prop="deliveryDate" label="到货日期" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getDeliveryDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.deliveryDate }}
              </span>
            </template>
          </el-table-column>

          <!-- 备注信息 -->
          <el-table-column prop="remark" label="备注信息" min-width="150">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.remark }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </template>

        <!-- 按单据分组 -->
        <template v-else>
          <!-- 所属组织 -->
          <el-table-column prop="orgName" label="所属组织" width="120" align="center">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.orgName }}
              </span>
            </template>
          </el-table-column>

          <!-- 客户 -->
          <el-table-column prop="customerName" label="客户" width="150">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.customerName }}
              </span>
            </template>
          </el-table-column>

          <!-- 分组行显示日期范围，明细行显示单据日期 -->
          <el-table-column prop="orderDate" label="单据时间" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orderDate }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="orderNo" label="单据编号" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getOrderNoSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orderNo }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="productName" label="商品名称" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getProductSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.productName }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="auxiliaryAttr" label="辅助属性" width="120">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.auxiliaryAttr }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column prop="warehouse" label="仓库" width="120">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getWarehouseSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.warehouse }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="unit" label="单位" width="80" align="center">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.unit }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column prop="quantity" label="数量" width="100" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.quantity }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="amount" label="金额" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.amount }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="storageStatus" label="出库状态" width="100" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getStorageStatusSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.storageStatus }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="unstockedQuantity" label="未出库数量" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedQuantity }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="unstockedAmount" label="未出库金额" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedAmount }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="deliveryDate" label="到货日期" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getDeliveryDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.deliveryDate }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="remark" label="备注信息" min-width="150">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.remark }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </template>
      </el-table>

      <!-- 分页 -->
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
import { reactive, ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import GoodSearch from '@/components/goodSearchConpoent/GoodSearchForm.vue'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent/type'

import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'
import {
  salesOrderTrackingFormUsingGet,
  salesOrderTrackingFormOpenApiExportUsingGet
} from '@/apis/openapi-apifox/xiaoshoudingdangenzongbiao'
import type { SalesOrderTrackingFormUsingGetParams } from '@/apis/openapi-apifox/types'

// 搜索组件引用
const goodSearchRef = ref()
/** 离开页面前先销毁树形表格，避免 Element Plus 卸载阻塞路由切换 */
const tableAlive = ref(true)

const mapOutboundState = (state?: number) => {
  if (state === 2) return '已出库'
  if (state === 0) return '未出库'
  if (state === 1) return '部分出库'
  return String(state ?? '')
}

const mapSaleFlatRow = (item: Record<string, unknown>, index: number) => ({
  id: index,
  orgName: String(item.frame ?? ''),
  customerName: String(item.customerName ?? item.customer ?? ''),
  orderDate: item.time ? String(item.time).slice(0, 10) : '',
  orderNo: String(item.number ?? ''),
  productName: String(item.goodsName ?? item.goods ?? ''),
  auxiliaryAttr: String(item.attr ?? ''),
  warehouse: String(item.warehouseName ?? item.warehouse ?? ''),
  unit: String(item.unit ?? ''),
  unitPrice: Number(item.price) || 0,
  quantity: Number(item.nums) || 0,
  amount: Number(item.total) || 0,
  storageStatus: mapOutboundState(Number(item.state)),
  unstockedQuantity: Number(item.unstockedQuantity) || 0,
  unstockedAmount: Number(item.unstockedAmount) || 0,
  deliveryDate: item.arrival ? String(item.arrival).slice(0, 10) : '',
  remark: String(item.itemRemark ?? ''),
  isChild: true
})

const groupSaleDocumentRows = (flatRows: ReturnType<typeof mapSaleFlatRow>[]) => {
  const groups = new Map<string, ReturnType<typeof mapSaleFlatRow>[]>()
  flatRows.forEach((row) => {
    const key = `${row.customerName}_${row.orderNo}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(row)
  })
  return Array.from(groups.values()).map((children, idx) => ({
    id: idx + 1,
    orgName: children[0].orgName,
    customerName: children[0].customerName,
    isChild: false,
    children: children.map((c, ci) => ({ ...c, id: `${idx}_${ci}` }))
  }))
}

const buildApiParams = (): SalesOrderTrackingFormUsingGetParams => {
  const params: SalesOrderTrackingFormUsingGetParams = {
    pageIndex: 1,
    pageSize: 99999
  }
  if (searchFormData.goods) params.goods = String(searchFormData.goods)
  if (searchFormData.number) params.number = String(searchFormData.number)
  if (searchFormData.customer) params.customer = String(searchFormData.customer)
  if (searchFormData.startTime) params.begintime = String(searchFormData.startTime)
  if (searchFormData.endTime) params.endtime = String(searchFormData.endTime)
  if (searchFormData.startArrival) params.beginarrival = String(searchFormData.startArrival)
  if (searchFormData.endArrival) params.endarrival = String(searchFormData.endArrival)
  if (searchFormData.warehouse) params.warehouse = String(searchFormData.warehouse)
  if (searchFormData.state) params.state = Number(searchFormData.state) as 0 | 1 | 2 | 3
  return params
}

async function loadData() {
  loading.value = true
  try {
    const res = await salesOrderTrackingFormUsingGet({ params: buildApiParams() })
    const { rows } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    const flat = rows.map((r, i) => mapSaleFlatRow(r as Record<string, unknown>, i))
    let treeData: ReturnType<typeof groupSaleDocumentRows> | ReturnType<typeof transformToProductStructure> = groupSaleDocumentRows(flat)
    if (isProductSort.value) {
      treeData = transformToProductStructure(treeData)
    } else {
      treeData = treeData.map((parent) => ({
        ...parent,
        children: [...(parent.children || [])].sort((a, b) => a.orderNo.localeCompare(b.orderNo))
      }))
      treeData.sort((a, b) => {
        const aFirst = a.children?.[0]?.orderNo || ''
        const bFirst = b.children?.[0]?.orderNo || ''
        return aFirst.localeCompare(bFirst)
      })
    }
    originalTableData.value = treeData
    currentTableData.value = JSON.parse(JSON.stringify(treeData))
    currentPage.value = 1
  } catch (error: unknown) {
    originalTableData.value = []
    currentTableData.value = []
    ElMessage.error(error instanceof Error ? error.message : '加载销售订单跟踪表失败')
  } finally {
    loading.value = false
  }
}

// 原始数据
const originalTableData = ref<any[]>([])

// 当前显示的表格数据
const currentTableData = ref<any[]>([])

// 搜索表单默认按单据排序
const searchFormData = reactive<SearchFormData>({
  goods: '',
  number: '',
  supplier: '',
  customer: null,
  people: null,
  user: null,
  startTime: '',
  endTime: '',
  startArrival: '',
  endArrival: '',
  examine: '',
  state: '',
  data: '',
  warehouse: '', // 仓库筛选
  sortType: '单据排序' // 默认按单据分组
})

// 搜索配置
const searchConfig = reactive<GoodSearchConfig>({
  showGoods: true,
  showNumber: true,
  showSupplier: false,
  showCustomer: true,
  showPeople: false,
  showBillDate: true,
  showArrivalDate: true,
  showUser: false,
  showExamine: false,
  showState: false,
  showRemark: false,
  showWarehouse: true,
  inline: true,
  customFields: [
    {
      key: 'sortType',
      type: 'select',
      label: '排列方式',
      options: [
        { label: '单据排序', value: '单据排序' },
        { label: '商品排序', value: '商品排序' }
      ]
    }
  ]
})

// 判断是否为商品排序模式
const isProductSort = computed(() => {
  return searchFormData.sortType === '商品排序'
})

// 同步搜索表单
const handleSearchFormUpdate = (newValue: SearchFormData) => {
  Object.assign(searchFormData, newValue)
}

// 提交搜索条件
const handleGoodSearch = (formData: SearchFormData) => {
  Object.assign(searchFormData, formData)
  loadData()
  ElMessage.success('数据已刷新')
}

// 将单据树转换为商品分组
const transformToProductStructure = (data: any[]) => {
  // 收集所有明细行
  const allChildren: any[] = []
  data.forEach((parent) => {
    if (parent.children && parent.children.length > 0) {
      parent.children.forEach((child: any) => {
        allChildren.push({ ...child })
      })
    }
  })

  // 按商品、辅助属性和仓库分组
  const productGroups: { [key: string]: any[] } = {}

  allChildren.forEach((child) => {
    const key = `${child.productName}_${child.auxiliaryAttr}_${child.warehouse}`
    if (!productGroups[key]) {
      productGroups[key] = []
    }
    productGroups[key].push(child)
  })

  // 构建商品分组树
  const productData = Object.entries(productGroups).map(([key, children], index) => {
    const firstChild = children[0]
    return {
      id: `product_${index + 1}`,
      productName: firstChild.productName,
      auxiliaryAttr: firstChild.auxiliaryAttr,
      warehouse: firstChild.warehouse,
      isChild: false,
      children: children.map((child, childIndex) => ({
        ...child,
        id: `product_${index + 1}_child_${childIndex + 1}`,
        // 分组行和明细行使用相同的商品、属性和仓库
        productName: firstChild.productName,
        auxiliaryAttr: firstChild.auxiliaryAttr,
        warehouse: firstChild.warehouse,
        isChild: true
      }))
    }
  })

  // 按商品名称的中文拼音排序
  return productData.sort((a, b) => a.productName.localeCompare(b.productName, 'zh-CN'))
}

// 应用搜索条件
const applySearchFilters = (formData: SearchFormData) => {
  let filteredData = JSON.parse(JSON.stringify(originalTableData.value))

  // 按条件筛选单据及明细
  filteredData = filteredData.filter(
    (parent: { customerName: string | string[]; children: any[] }) => {
      // 筛选客户
      if (formData.customer && !parent.customerName.includes(formData.customer as string)) {
        return false
      }

      // 在明细中筛选商品名称
      if (formData.goods) {
        const hasMatchingChild = parent.children?.some(
          (child: { productName: string | string[] }) =>
            child.productName.includes(formData.goods as string)
        )
        if (!hasMatchingChild) return false
      }

      // 筛选单据编号
      if (formData.number) {
        const hasMatchingChild = parent.children?.some((child: { orderNo: string | string[] }) =>
          child.orderNo.includes(formData.number as string)
        )
        if (!hasMatchingChild) return false
      }

      // 筛选仓库
      if (formData.warehouse) {
        const warehouseValue = formData.warehouse
        const filteredChildren = parent.children?.filter(
          (child: { warehouse: any }) => child.warehouse === warehouseValue
        )
        if (!filteredChildren || filteredChildren.length === 0) return false
        parent.children = filteredChildren
      }

      // 筛选单据日期范围
      if (formData.startTime || formData.endTime) {
        const filteredChildren = parent.children?.filter(
          (child: { orderDate: string | number | Date }) => {
            const orderDate = new Date(child.orderDate)
            const startDate = formData.startTime ? new Date(formData.startTime) : null
            const endDate = formData.endTime ? new Date(formData.endTime) : null

            if (startDate && orderDate < startDate) return false
            if (endDate && orderDate > endDate) return false
            return true
          }
        )
        if (!filteredChildren || filteredChildren.length === 0) return false
        parent.children = filteredChildren
      }

      // 筛选到货日期范围
      if (formData.startArrival || formData.endArrival) {
        const filteredChildren = parent.children?.filter(
          (child: { deliveryDate: string | number | Date }) => {
            const deliveryDate = new Date(child.deliveryDate)
            const startDate = formData.startArrival ? new Date(formData.startArrival) : null
            const endDate = formData.endArrival ? new Date(formData.endArrival) : null

            if (startDate && deliveryDate < startDate) return false
            if (endDate && deliveryDate > endDate) return false
            return true
          }
        )
        if (!filteredChildren || filteredChildren.length === 0) return false
        parent.children = filteredChildren
      }

      return true
    }
  )

  // 应用排序
  if (formData.sortType === '商品排序') {
    // 按商品分组并排序
    filteredData = transformToProductStructure(filteredData)
  } else if (formData.sortType === '单据排序') {
    // 按单据编号排序明细
    filteredData = filteredData.map((parent: { children: any }) => {
      const sortedChildren = [...(parent.children || [])].sort((a, b) =>
        a.orderNo.localeCompare(b.orderNo)
      )
      return { ...parent, children: sortedChildren }
    })

    // 按单据编号排序分组
    filteredData.sort((a: any, b: any) => {
      const aFirstOrder = a.children?.[0]?.orderNo || ''
      const bFirstOrder = b.children?.[0]?.orderNo || ''
      return aFirstOrder.localeCompare(bFirstOrder)
    })
  }

  // 更新当前显示的数据
  currentTableData.value = filteredData
  currentPage.value = 1 // 返回第一页
}

// 刷新并重置搜索条件
const handleRefresh = () => {
  Object.assign(searchFormData, {
    goods: '',
    number: '',
    supplier: '',
    customer: '',
    startTime: '',
    endTime: '',
    startArrival: '',
    endArrival: '',
    warehouse: '',
    sortType: '单据排序'
  })
  goodSearchRef.value?.resetForm()
  loadData()
  ElMessage.success('数据已刷新')
}

// 导出报表
const handleExport = async () => {
  try {
    const res = await salesOrderTrackingFormOpenApiExportUsingGet({ params: buildApiParams() })
    downloadExportBlob(res, `销售订单跟踪表_${new Date().toISOString().split('T')[0]}.xlsx`)
    ElMessage.success('数据已刷新')
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  }
}

// 分页状态
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)

// 分页总数仅统计分组行
const total = computed(() => {
  return currentTableData.value.length
})

// 对分组行分页
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return currentTableData.value.slice(start, end)
})

// 分页事件
const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

// 分组行的汇总显示
const getDateRange = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const dates = parent.children.map((child: any) => child.orderDate)
  const minDate = Math.min(...dates.map((date: string) => new Date(date).getTime()))
  const maxDate = Math.max(...dates.map((date: string) => new Date(date).getTime()))
  return `${new Date(minDate).toISOString().split('T')[0]} ~ ${new Date(maxDate).toISOString().split('T')[0]}`
}

const getOrderNoSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const orderNos = [...new Set(parent.children.map((child: any) => child.orderNo))]
  return orderNos.length === 1 ? orderNos[0] : `${orderNos.length}张单据`
}

const getProductSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const products = [...new Set(parent.children.map((child: any) => child.productName))]
  return products.length === 1 ? products[0] : `${products.length}种商品`
}

const getOrgSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const orgs = [...new Set(parent.children.map((child: any) => child.orgName))]
  return orgs.length === 1 ? orgs[0] : `${orgs.length}个组织`
}

const getCustomerSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const customers = [...new Set(parent.children.map((child: any) => child.customerName))]
  return customers.length === 1 ? customers[0] : `${customers.length}个客户`
}

const getWarehouseSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const warehouses = [...new Set(parent.children.map((child: any) => child.warehouse))]
  return warehouses.length === 1 ? warehouses[0] : `${warehouses.length}个仓库`
}

const getTotalQuantity = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return 0
  return parent.children.reduce((sum: number, child: any) => sum + child.quantity, 0)
}

const getTotalAmount = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return 0
  return parent.children.reduce((sum: number, child: any) => sum + child.amount, 0)
}

const getStorageStatusSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const statusCount: Record<string, number> = {}
  parent.children.forEach((child: any) => {
    statusCount[child.storageStatus] = (statusCount[child.storageStatus] || 0) + 1
  })
  return Object.entries(statusCount)
    .map(([status, count]) => `${status}(${count})`)
    .join(', ')
}

const getTotalUnstockedQuantity = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return 0
  return parent.children.reduce((sum: number, child: any) => sum + child.unstockedQuantity, 0)
}

const getTotalUnstockedAmount = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return 0
  return parent.children.reduce((sum: number, child: any) => sum + child.unstockedAmount, 0)
}

const getDeliveryDateRange = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const dates = parent.children.map((child: any) => child.deliveryDate)
  const minDate = Math.min(...dates.map((date: string) => new Date(date).getTime()))
  const maxDate = Math.max(...dates.map((date: string) => new Date(date).getTime()))
  return `${new Date(minDate).toISOString().split('T')[0]} ~ ${new Date(maxDate).toISOString().split('T')[0]}`
}

// 商品分组的平均单价
const getAverageUnitPrice = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return 0
  const totalAmount = parent.children.reduce((sum: number, child: any) => sum + child.amount, 0)
  const totalQuantity = parent.children.reduce((sum: number, child: any) => sum + child.quantity, 0)
  return totalQuantity > 0 ? (totalAmount / totalQuantity).toFixed(2) : 0
}

const calculateUnitPrice = (child: any) => {
  return child.quantity > 0 ? (child.amount / child.quantity).toFixed(2) : 0
}

// 页面生命周期
onBeforeUnmount(() => {
  tableAlive.value = false
  loading.value = false
  currentTableData.value = []
  originalTableData.value = []
  goodSearchRef.value?.dispose?.()
})

onMounted(() => {
  loadData()
})
</script>

<style scoped>
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

.parent-row {
  font-weight: 600;
  color: #303133;
}

.child-row {
  color: #606266;
}

.parent-placeholder {
  color: #c0c4cc;
  font-style: italic;
}
</style>
