<!--
 * @Description: 搜索组件-客户搜索（条件+分页）
-->
<template>
  <div class="customer-search-container">
    <GoodSearchForm v-model="searchForm" :config="searchConfig" @search="handleSearch" />
    
    <!-- 搜索结果列表 -->
    <div v-if="searchResults.length > 0" class="search-results">
      <el-table
        :data="searchResults"
        stripe
        highlight-current-row
        @row-click="handleRowClick"
        style="width: 100%; margin-top: 16px;"
        max-height="400"
      >
        <el-table-column prop="name" label="客户名称" width="200" />
        <el-table-column prop="code" label="客户编号" width="150" />
        <el-table-column prop="category" label="类别" width="120" />
        <el-table-column prop="level" label="等级" width="100" />
        <el-table-column prop="contact" label="联系人" width="120" />
        <el-table-column prop="phone" label="联系电话" width="150" />
      </el-table>
    </div>
    
    <!-- 无搜索结果提示 -->
    <div v-if="hasSearched && searchResults.length === 0" class="no-results">
      <el-empty description="未找到匹配的客户" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import GoodSearchForm from './GoodSearchForm.vue'
import type { SearchFormData, GoodSearchConfig } from './type'
import type { CustomerListItem } from '@/apis/common/type'
import { CustomerAPI } from '@/apis/basicdata/customer'

// 定义分页数据类型
interface PaginationModel {
  pageIndex: number
  pageSize: number
}

// 定义 props
const props = defineProps<{
  pagination?: PaginationModel
}>()

// 定义 emits
const emit = defineEmits<{
  'update:pagination': [value: PaginationModel]
  search: [params: any]
}>()

/**
 * 搜索表单数据
 */
const searchForm = ref<SearchFormData>({})

/**
 * 搜索结果列表
 */
const searchResults = ref<CustomerListItem[]>([])

/**
 * 是否已搜索过
 */
const hasSearched = ref(false)

/**
 * 搜索配置
 */
const searchConfig = reactive<GoodSearchConfig>({
  // 使用内联模式（不显示popover触发按钮）
  inline: true,
  
  // 隐藏不需要的字段
  showSupplier: false,
  showCustomer: false,
  showWarehouse: false,
  showAccount: false,
  showGoods: false,
  showNumber: false,
  showBillDate: false,
  showArrivalDate: false,
  showExamine: false,
  showState: false,
  showPeople: false,
  showUser: true,  // 启用用户搜索（所属用户）
  userPlaceholder: '请选择所属用户',  // 自定义用户字段的占位符
  showRemark: false,

  // 自定义字段（参考截图）
  customFields: [
    { key: 'customerName', label: '请输入客户名称', type: 'input' },
    { key: 'customerCode', label: '请输入客户编号', type: 'input' },
    {
      key: 'customerCategory',
      label: '请选择客户类别',
      type: 'select',
      options: [
        { label: '零售', value: '零售' },
        { label: '批发', value: '批发' },
        { label: '电商', value: '电商' },
        { label: 'VIP', value: 'VIP' }
      ]
    },
    {
      key: 'customerLevel',
      label: '请选择客户等级',
      type: 'select',
      options: [
        { label: 'A', value: 'A' },
        { label: 'B', value: 'B' },
        { label: 'C', value: 'C' },
        { label: 'D', value: 'D' }
      ]
    },
    { key: 'contactPerson', label: '请输入联系人', type: 'input' },
    { key: 'contactPhone', label: '请输入联系电话', type: 'input' },
    { key: 'remark', label: '请输入备注信息', type: 'input' }
  ]
})

/**
 * 处理搜索事件
 */
async function handleSearch(formData: SearchFormData) {
  hasSearched.value = true
  const searchParams = {
    name: formData.customerName,
    number: formData.customerCode,
    category: formData.customerCategory,
    grade: formData.customerLevel,
    contact_person: formData.contactPerson,
    telephone: formData.contactPhone,
    username: formData.user ?? undefined,
    memo: formData.remark,
    pageIndex: props.pagination?.pageIndex || 1,
    pageSize: props.pagination?.pageSize || 200
  }

  try {
    const result = await CustomerAPI.getCustomerList(searchParams)
    const rows = result?.data?.rows || []
    searchResults.value = rows.map((row: any) => ({
      id: String(row.id ?? ''),
      name: row.name || '',
      code: row.number || row.code || '',
      category: row.category || '',
      level: row.grade || row.level || '',
      contact: row.contact_person || '',
      phone: row.telephone || ''
    })) as CustomerListItem[]
  } catch (error) {
    console.error('搜索客户失败:', error)
    searchResults.value = []
    ElMessage.error(error instanceof Error ? error.message : '搜索客户失败')
  }
}

/**
 * 处理表格行点击事件（选择客户）
 */
function handleRowClick(row: CustomerListItem) {
  // 触发搜索事件，传递选中的客户信息
  emit('search', {
    ...row,
    customerName: row.name,
    customerId: row.id
  })
  ElMessage.success(`已选择客户：${row.name}`)
}

// 暴露方法给父组件
defineExpose({
  getFormData: () => searchForm.value,
  resetSearch: () => {
    searchForm.value = {}
  },
  triggerSearch: () => {
    handleSearch(searchForm.value)
  },
  searchForm
})
</script>


