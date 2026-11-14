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
        <!-- 商品排序模式下的列顺序 -->
        <template v-if="isProductSort">
          <!-- 商品名称列 -->
          <el-table-column prop="productName" label="商品名称" width="150">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.productName }}
              </span>
            </template>
          </el-table-column>

          <!-- 辅助属性列 -->
          <el-table-column prop="auxiliaryAttr" label="辅助属性" width="120">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.auxiliaryAttr }}
              </span>
            </template>
          </el-table-column>

          <!-- 仓库列 -->
          <el-table-column prop="warehouse" label="仓库" width="120">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.warehouse }}
              </span>
            </template>
          </el-table-column>

          <!-- 所属组织列 -->
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

          <!-- 供应商列 -->
          <el-table-column prop="supplierName" label="供应商" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getSupplierSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.supplierName }}
              </span>
            </template>
          </el-table-column>

          <!-- 单据时间�?-->
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

          <!-- 单据编号�?-->
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

          <!-- 单位�?-->
          <el-table-column prop="unit" label="单位" width="80" align="center">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.unit }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <!-- 单价�?-->
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

          <!-- 数量�?-->
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

          <!-- 金额�?-->
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

          <!-- 入库状态列 -->
          <el-table-column prop="storageStatus" label="入库状态" width="100" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getStorageStatusSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.storageStatus }}
              </span>
            </template>
          </el-table-column>

          <!-- 未入库数量列 -->
          <el-table-column prop="unstockedQuantity" label="未入库数量" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedQuantity }}
              </span>
            </template>
          </el-table-column>

          <!-- 未入库金额列 -->
          <el-table-column prop="unstockedAmount" label="未入库金额" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedAmount }}
              </span>
            </template>
          </el-table-column>

          <!-- 到货日期�?-->
          <el-table-column prop="arrivalDate" label="到货日期" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getArrivalDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.arrivalDate }}
              </span>
            </template>
          </el-table-column>

          <!-- 备注信息�?-->
          <el-table-column prop="remark" label="备注信息" min-width="150">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.remark }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </template>

        <!-- 单据排序模式下的列顺序 -->
        <template v-else>
          <!-- 所属组织列 -->
          <el-table-column prop="orgName" label="所属组织" width="120" align="center">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.orgName }}
              </span>
            </template>
          </el-table-column>

          <!-- 供应商列 -->
          <el-table-column prop="supplierName" label="供应商" width="150">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.supplierName }}
              </span>
            </template>
          </el-table-column>

          <!-- 其他数据�?- 在父级行显示汇总信息，子级行显示详细信�?-->
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

          <el-table-column prop="storageStatus" label="入库状态" width="100" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getStorageStatusSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.storageStatus }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="unstockedQuantity" label="未入库数量" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedQuantity }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="unstockedAmount" label="未入库金额" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedAmount }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="arrivalDate" label="到货日期" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getArrivalDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.arrivalDate }}
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
import { reactive, ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import GoodSearch from '@/components/goodSearchConpoent/GoodSearchForm.vue'
import type { SearchFormData, GoodSearchConfig } from '@/components/goodSearchConpoent/type'

import { unwrapPage, downloadExportBlob } from '@/utils/reportMappers'
import {
  purchaseOrderTrackingFormUsingGet,
  purchaseOrderTrackingFormOpenApiExportUsingGet
} from '@/apis/openapi-apifox/caigoudingdangenzongbiao'
import type { PurchaseOrderTrackingFormUsingGetParams } from '@/apis/openapi-apifox/types'

// 搜索组件引用
const goodSearchRef = ref()
/** 离开页面前先销毁树形表格，避免 Element Plus 卸载阻塞路由切换 */
const tableAlive = ref(true)

const mapInboundState = (state?: number) => {
  if (state === 2) return '已入库'
  if (state === 0) return '未入库'
  if (state === 1) return '部分入库'
  return String(state ?? '')
}

const mapPurchaseFlatRow = (item: Record<string, unknown>, index: number) => ({
  id: index,
  orgName: String(item.frame ?? ''),
  supplierName: String(item.supplierName ?? item.supplier ?? ''),
  orderDate: item.time ? String(item.time).slice(0, 10) : '',
  orderNo: String(item.number ?? ''),
  productName: String(item.goodsName ?? item.goods ?? ''),
  auxiliaryAttr: String(item.attr ?? ''),
  warehouse: String(item.warehouseName ?? item.warehouse ?? ''),
  unit: String(item.unit ?? ''),
  quantity: Number(item.nums) || 0,
  amount: Number(item.total) || 0,
  storageStatus: mapInboundState(Number(item.state)),
  unstockedQuantity: Number(item.unstockedQuantity) || 0,
  unstockedAmount: Number(item.unstockedAmount) || 0,
  arrivalDate: item.arrival ? String(item.arrival).slice(0, 10) : '',
  remark: String(item.itemRemark ?? ''),
  isChild: true
})

const groupPurchaseDocumentRows = (flatRows: ReturnType<typeof mapPurchaseFlatRow>[]) => {
  const groups = new Map<string, ReturnType<typeof mapPurchaseFlatRow>[]>()
  flatRows.forEach((row) => {
    const key = `${row.supplierName}_${row.orderNo}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(row)
  })
  return Array.from(groups.values()).map((children, idx) => ({
    id: idx + 1,
    orgName: children[0].orgName,
    supplierName: children[0].supplierName,
    isChild: false,
    children: children.map((c, ci) => ({ ...c, id: `${idx}_${ci}` }))
  }))
}

const buildApiParams = (): PurchaseOrderTrackingFormUsingGetParams => {
  const params: PurchaseOrderTrackingFormUsingGetParams = {
    pageIndex: 1,
    pageSize: 99999
  }
  if (searchFormData.goods) params.goods = String(searchFormData.goods)
  if (searchFormData.number) params.number = String(searchFormData.number)
  if (searchFormData.supplier) params.supplier = String(searchFormData.supplier)
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
    const res = await purchaseOrderTrackingFormUsingGet({ params: buildApiParams() })
    const { rows } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    const flat = rows.map((r, i) => mapPurchaseFlatRow(r as Record<string, unknown>, i))
    let treeData: ReturnType<typeof groupPurchaseDocumentRows> | ReturnType<typeof transformToProductStructure> = groupPurchaseDocumentRows(flat)
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
    ElMessage.error(error instanceof Error ? error.message : '加载采购订单跟踪表失败')
  } finally {
    loading.value = false
  }
}

// 原始表格数据
const originalTableData = ref<any[]>([])

// 当前显示的表格数据
const currentTableData = ref<any[]>([])

// 搜索表单数据 - 设置默认排序为"单据排序"
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
  warehouse: '', // 仓库字段
  sortType: '单据排序' // 默认选择单据排序
})

// 搜索配置 - 使用默认的仓库搜索弹窗
const searchConfig = reactive<GoodSearchConfig>({
  showGoods: true,
  showNumber: true,
  showSupplier: true,
  showCustomer: false,
  showPeople: false,
  showBillDate: true,
  showArrivalDate: true,
  showUser: false,
  showExamine: false,
  showState: false,
  showRemark: false,
  showWarehouse: true, // 启用默认的仓库搜索
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

// 计算是否处于商品排序模式
const isProductSort = computed(() => {
  return searchFormData.sortType === '商品排序'
})

// 处理搜索表单更新
const handleSearchFormUpdate = (newValue: SearchFormData) => {
  Object.assign(searchFormData, newValue)
}

// 处理搜索组件的搜索事件
const handleGoodSearch = (formData: SearchFormData) => {
  Object.assign(searchFormData, formData)
  loadData()
  ElMessage.success('数据已刷新')
}

// 将原始数据转换为商品排序模式的数据结构
const transformToProductStructure = (data: any[]) => {
  const allChildren: any[] = []
  data.forEach((parent) => {
    if (parent.children && parent.children.length > 0) {
      parent.children.forEach((child: any) => {
        allChildren.push({ ...child })
      })
    }
  })

  const productGroups: { [key: string]: any[] } = {}

  allChildren.forEach((child) => {
    const key = `${child.productName}_${child.auxiliaryAttr}_${child.warehouse}`
    if (!productGroups[key]) {
      productGroups[key] = []
    }
    productGroups[key].push(child)
  })

  const productData = Object.entries(productGroups).map(([, children], index) => {
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
        productName: firstChild.productName,
        auxiliaryAttr: firstChild.auxiliaryAttr,
        warehouse: firstChild.warehouse,
        isChild: true
      }))
    }
  })

  return productData.sort((a, b) => a.productName.localeCompare(b.productName, 'zh-CN'))
}

// 刷新功能
const handleRefresh = () => {
  if (goodSearchRef.value) {
    goodSearchRef.value.resetForm()
  }
  Object.assign(searchFormData, {
    goods: '',
    number: '',
    supplier: '',
    startTime: '',
    endTime: '',
    startArrival: '',
    endArrival: '',
    warehouse: '',
    sortType: '单据排序'
  })
  loadData()
  ElMessage.success('数据已刷新')
}

// 导出功能实现
const handleExport = async () => {
  try {
    const res = await purchaseOrderTrackingFormOpenApiExportUsingGet({ params: buildApiParams() })
    downloadExportBlob(res, `采购订单跟踪表_${new Date().toISOString().split('T')[0]}.xlsx`)
    ElMessage.success('数据已刷新')
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  }
}

// 分页相关
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)

// 计算总数据条数（只计算父级行）
const total = computed(() => {
  return currentTableData.value.length
})

// 当前页数据（只包含父级行）
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

// 辅助函数 - 父级行显示汇总信息
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
  return orderNos.length === 1 ? orderNos[0] : `${orderNos.length}个单据`
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

const getSupplierSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const suppliers = [...new Set(parent.children.map((child: any) => child.supplierName))]
  return suppliers.length === 1 ? suppliers[0] : `${suppliers.length}个供应商`
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

const getArrivalDateRange = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const dates = parent.children.map((child: any) => child.arrivalDate)
  const minDate = Math.min(...dates.map((date: string) => new Date(date).getTime()))
  const maxDate = Math.max(...dates.map((date: string) => new Date(date).getTime()))
  return `${new Date(minDate).toISOString().split('T')[0]} ~ ${new Date(maxDate).toISOString().split('T')[0]}`
}

// 商品排序模式下的新增辅助函数
const getAverageUnitPrice = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return 0
  const totalAmount = parent.children.reduce((sum: number, child: any) => sum + child.amount, 0)
  const totalQuantity = parent.children.reduce((sum: number, child: any) => sum + child.quantity, 0)
  return totalQuantity > 0 ? (totalAmount / totalQuantity).toFixed(2) : 0
}

const calculateUnitPrice = (child: any) => {
  return child.quantity > 0 ? (child.amount / child.quantity).toFixed(2) : 0
}

onBeforeUnmount(() => {
  tableAlive.value = false
  loading.value = false
  currentTableData.value = []
  originalTableData.value = []
  goodSearchRef.value?.dispose?.()
})

// 初始化
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
