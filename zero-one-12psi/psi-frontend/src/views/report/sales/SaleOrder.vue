<template>
  <div class="sys area">
    <!-- ������ť���� -->
    <div class="operation-bar">
      <div class="operation-left">
        <!-- ʹ��������� -->
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
          ����
        </el-button>
        <el-button type="info" @click="handleRefresh" class="action-btn">
          <el-icon><Refresh /></el-icon>
          ˢ��
        </el-button>
      </div>
    </div>

    <el-divider class="custom-divider" />

    <!-- �������� - ռ����Ҫ�ռ� -->
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
        <!-- ��Ʒ����ģʽ�µ���˳�� -->
        <template v-if="isProductSort">
          <!-- ��Ʒ������ -->
          <el-table-column prop="productName" label="��Ʒ����" width="150">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.productName }}
              </span>
            </template>
          </el-table-column>

          <!-- ���������� -->
          <el-table-column prop="auxiliaryAttr" label="��������" width="120">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.auxiliaryAttr }}
              </span>
            </template>
          </el-table-column>

          <!-- �ֿ��� -->
          <el-table-column prop="warehouse" label="�ֿ�" width="120">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.warehouse }}
              </span>
            </template>
          </el-table-column>

          <!-- ������֯�� -->
          <el-table-column prop="orgName" label="������֯" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getOrgSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orgName }}
              </span>
            </template>
          </el-table-column>

          <!-- ��Ӧ���� -->
          <el-table-column prop="customerName" label="�ͻ�" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getCustomerSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.customerName }}
              </span>
            </template>
          </el-table-column>

          <!-- ����ʱ���� -->
          <el-table-column prop="orderDate" label="����ʱ��" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orderDate }}
              </span>
            </template>
          </el-table-column>

          <!-- ���ݱ���� -->
          <el-table-column prop="orderNo" label="���ݱ��" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getOrderNoSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orderNo }}
              </span>
            </template>
          </el-table-column>

          <!-- ��λ�� -->
          <el-table-column prop="unit" label="��λ" width="80" align="center">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.unit }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <!-- ������ -->
          <el-table-column prop="unitPrice" label="����" width="100" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getAverageUnitPrice(scope.row) }}
              </span>
              <span v-else>
                {{ calculateUnitPrice(scope.row) }}
              </span>
            </template>
          </el-table-column>

          <!-- ������ -->
          <el-table-column prop="quantity" label="����" width="100" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.quantity }}
              </span>
            </template>
          </el-table-column>

          <!-- ����� -->
          <el-table-column prop="amount" label="���" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.amount }}
              </span>
            </template>
          </el-table-column>

          <!-- ����״̬�� -->
          <el-table-column prop="storageStatus" label="����״̬" width="100" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getStorageStatusSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.storageStatus }}
              </span>
            </template>
          </el-table-column>

          <!-- δ���������� -->
          <el-table-column prop="unstockedQuantity" label="δ��������" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedQuantity }}
              </span>
            </template>
          </el-table-column>

          <!-- δ�������� -->
          <el-table-column prop="unstockedAmount" label="δ������" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedAmount }}
              </span>
            </template>
          </el-table-column>

          <!-- ���������� -->
          <el-table-column prop="deliveryDate" label="��������" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getDeliveryDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.deliveryDate }}
              </span>
            </template>
          </el-table-column>

          <!-- ��ע��Ϣ�� -->
          <el-table-column prop="remark" label="��ע��Ϣ" min-width="150">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.remark }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </template>

        <!-- ��������ģʽ�µ���˳��ԭ˳�� -->
        <template v-else>
          <!-- ������֯�� -->
          <el-table-column prop="orgName" label="������֯" width="120" align="center">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.orgName }}
              </span>
            </template>
          </el-table-column>

          <!-- ��Ӧ���� -->
          <el-table-column prop="customerName" label="�ͻ�" width="150">
            <template #default="scope">
              <span class="parent-row">
                {{ scope.row.customerName }}
              </span>
            </template>
          </el-table-column>

          <!-- ���������� - �ڸ�������ʾ������Ϣ���Ӽ�����ʾ��ϸ��Ϣ -->
          <el-table-column prop="orderDate" label="����ʱ��" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orderDate }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="orderNo" label="���ݱ��" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getOrderNoSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.orderNo }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="productName" label="��Ʒ����" width="150">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getProductSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.productName }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="auxiliaryAttr" label="��������" width="120">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.auxiliaryAttr }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column prop="warehouse" label="�ֿ�" width="120">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getWarehouseSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.warehouse }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="unit" label="��λ" width="80" align="center">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.unit }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column prop="quantity" label="����" width="100" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.quantity }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="amount" label="���" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.amount }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="storageStatus" label="����״̬" width="100" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getStorageStatusSummary(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.storageStatus }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="unstockedQuantity" label="δ��������" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedQuantity(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedQuantity }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="unstockedAmount" label="δ������" width="120" align="right">
            <template #default="scope">
              <span v-if="!scope.row.isChild" class="parent-row">
                {{ getTotalUnstockedAmount(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.unstockedAmount }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="deliveryDate" label="��������" width="120" align="center">
            <template #default="scope">
              <span v-if="!scope.row.isChild">
                {{ getDeliveryDateRange(scope.row) }}
              </span>
              <span v-else>
                {{ scope.row.deliveryDate }}
              </span>
            </template>
          </el-table-column>

          <el-table-column prop="remark" label="��ע��Ϣ" min-width="150">
            <template #default="scope">
              <span v-if="scope.row.isChild">
                {{ scope.row.remark }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </template>
      </el-table>

      <!-- ��ҳ���� -->
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

// �����������
const goodSearchRef = ref()
/** 离开页面前先销毁树形表格，避免 Element Plus 卸载阻塞路由切换 */
const tableAlive = ref(true)

const mapOutboundState = (state?: number) => {
  if (state === 2) return '�ѳ���'
  if (state === 0) return 'δ����'
  if (state === 1) return '���ֳ���'
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
  if (searchFormData.supplier) params.customer = String(searchFormData.supplier)
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

// ԭʼ����
const originalTableData = ref<any[]>([])

// ��ǰ��ʾ�ı�������
const currentTableData = ref<any[]>([])

// ������������ - ����Ĭ������Ϊ"��������"
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
  warehouse: '', // �ֿ��ֶ�
  sortType: '单据排序' // Ĭ��ѡ�񵥾�����
})

// �������� - ʹ��Ĭ�ϵĲֿ���������
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
  showWarehouse: true, // ����Ĭ�ϵĲֿ�����
  inline: true,
  customFields: [
    {
      key: 'sortType',
      type: 'select',
      label: '���з�ʽ',
      options: [
        { label: '单据排序', value: '单据排序' },
        { label: '商品排序', value: '商品排序' }
      ]
    }
  ]
})

// �����Ƿ�����Ʒ����ģʽ
const isProductSort = computed(() => {
  return searchFormData.sortType === '商品排序'
})

// ����������������
const handleSearchFormUpdate = (newValue: SearchFormData) => {
  Object.assign(searchFormData, newValue)
}

// ������������������¼�
const handleGoodSearch = (formData: SearchFormData) => {
  Object.assign(searchFormData, formData)
  loadData()
  ElMessage.success('数据已刷新')
}

// ��ԭʼ����ת��Ϊ��Ʒ����ģʽ�����ݽṹ
const transformToProductStructure = (data: any[]) => {
  // �����ռ������ӽڵ�
  const allChildren: any[] = []
  data.forEach((parent) => {
    if (parent.children && parent.children.length > 0) {
      parent.children.forEach((child: any) => {
        allChildren.push({ ...child })
      })
    }
  })

  // ����Ʒ���ơ��������ԡ��ֿ����
  const productGroups: { [key: string]: any[] } = {}

  allChildren.forEach((child) => {
    const key = `${child.productName}_${child.auxiliaryAttr}_${child.warehouse}`
    if (!productGroups[key]) {
      productGroups[key] = []
    }
    productGroups[key].push(child)
  })

  // ������Ʒ�������ݽṹ
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
        // �����ݵ���Ʒ���ơ��������ԡ��ֿ��������һ��
        productName: firstChild.productName,
        auxiliaryAttr: firstChild.auxiliaryAttr,
        warehouse: firstChild.warehouse,
        isChild: true
      }))
    }
  })

  // ����Ʒ����ƴ������ĸ����
  return productData.sort((a, b) => a.productName.localeCompare(b.productName, 'zh-CN'))
}

// Ӧ����������
const applySearchFilters = (formData: SearchFormData) => {
  let filteredData = JSON.parse(JSON.stringify(originalTableData.value))

  // ��������������������
  filteredData = filteredData.filter(
    (parent: { customerName: string | string[]; children: any[] }) => {
      // ���˿ͻ�
      if (formData.supplier && !parent.customerName.includes(formData.supplier as string)) {
        return false
      }

      // ������Ʒ���ƣ����Ӽ��в��ң�
      if (formData.goods) {
        const hasMatchingChild = parent.children?.some(
          (child: { productName: string | string[] }) =>
            child.productName.includes(formData.goods as string)
        )
        if (!hasMatchingChild) return false
      }

      // ���˵��ݱ��
      if (formData.number) {
        const hasMatchingChild = parent.children?.some((child: { orderNo: string | string[] }) =>
          child.orderNo.includes(formData.number as string)
        )
        if (!hasMatchingChild) return false
      }

      // ���˲ֿ� - ʹ��Ĭ�ϵĲֿ������������ַ�����
      if (formData.warehouse) {
        const warehouseValue = formData.warehouse
        const filteredChildren = parent.children?.filter(
          (child: { warehouse: any }) => child.warehouse === warehouseValue
        )
        if (!filteredChildren || filteredChildren.length === 0) return false
        parent.children = filteredChildren
      }

      // ���˵������ڷ�Χ
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

      // ���˷������ڷ�Χ
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

  // ������
  if (formData.sortType === '��Ʒ����') {
    // ��Ʒ����ת��Ϊ��Ʒ����ṹ������Ʒ����ƴ������
    filteredData = transformToProductStructure(filteredData)
  } else if (formData.sortType === '��������') {
    // �������򣺰����ݱ�Ŵ�С��������
    filteredData = filteredData.map((parent: { children: any }) => {
      const sortedChildren = [...(parent.children || [])].sort((a, b) =>
        a.orderNo.localeCompare(b.orderNo)
      )
      return { ...parent, children: sortedChildren }
    })

    // ͬʱ�����ݱ�ŶԸ����н�������
    filteredData.sort((a: any, b: any) => {
      const aFirstOrder = a.children?.[0]?.orderNo || ''
      const bFirstOrder = b.children?.[0]?.orderNo || ''
      return aFirstOrder.localeCompare(bFirstOrder)
    })
  }

  // ���µ�ǰ��ʾ������
  currentTableData.value = filteredData
  currentPage.value = 1 // ���õ���һҳ
}

// ˢ�¹���
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
    sortType: '��������'
  })
  loadData()
  ElMessage.success('数据已刷新')
}

// ��������ʵ��
const handleExport = async () => {
  try {
    const res = await salesOrderTrackingFormOpenApiExportUsingGet({ params: buildApiParams() })
    downloadExportBlob(res, `销售订单跟踪表_${new Date().toISOString().split('T')[0]}.xlsx`)
    ElMessage.success('数据已刷新')
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  }
}

// ׼����������
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)

// ����������������ֻ���㸸���У�
const total = computed(() => {
  return currentTableData.value.length
})

// ��ǰҳ���ݣ�ֻ���������У�
const currentPageData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return currentTableData.value.slice(start, end)
})

// ��ҳ����
const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

// �������� - ��������ʾ������Ϣ
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
  return orderNos.length === 1 ? orderNos[0] : `${orderNos.length}������`
}

const getProductSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const products = [...new Set(parent.children.map((child: any) => child.productName))]
  return products.length === 1 ? products[0] : `${products.length}����Ʒ`
}

const getOrgSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const orgs = [...new Set(parent.children.map((child: any) => child.orgName))]
  return orgs.length === 1 ? orgs[0] : `${orgs.length}����֯`
}

const getCustomerSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const customers = [...new Set(parent.children.map((child: any) => child.customerName))]
  return customers.length === 1 ? customers[0] : `${customers.length}���ͻ�`
}

const getWarehouseSummary = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return '-'
  const warehouses = [...new Set(parent.children.map((child: any) => child.warehouse))]
  return warehouses.length === 1 ? warehouses[0] : `${warehouses.length}���ֿ�`
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

// ��Ʒ����ģʽ�µ�������������
const getAverageUnitPrice = (parent: any) => {
  if (!parent.children || parent.children.length === 0) return 0
  const totalAmount = parent.children.reduce((sum: number, child: any) => sum + child.amount, 0)
  const totalQuantity = parent.children.reduce((sum: number, child: any) => sum + child.quantity, 0)
  return totalQuantity > 0 ? (totalAmount / totalQuantity).toFixed(2) : 0
}

const calculateUnitPrice = (child: any) => {
  return child.quantity > 0 ? (child.amount / child.quantity).toFixed(2) : 0
}

// ��ʼ��
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
