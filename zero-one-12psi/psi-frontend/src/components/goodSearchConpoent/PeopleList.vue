<!--
 * @Description: 搜索组件-获取人员列表（条件+分页）
-->
<template>
  <div class="people-search-container">
    <GoodSearchForm v-model="searchForm" :config="searchConfig" @search="handleSearch" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon><el-button @click="loadPeople">重新加载人员</el-button></el-alert>
    
    <!-- 搜索结果列表 -->
    <div v-if="searchResults.length > 0" class="search-results">
      <el-table
        v-loading="loading"
        :data="searchResults"
        stripe
        highlight-current-row
        @row-click="handleRowClick"
        style="width: 100%; margin-top: 16px;"
        max-height="400"
      >
        <el-table-column prop="name" label="人员名称" width="150" />
        <el-table-column prop="employeeNo" label="人员编号" width="150" />
        <el-table-column prop="gender" label="性别" width="100" />
        <el-table-column prop="phone" label="联系电话" width="150" />
        <el-table-column prop="deptName" label="所属部门" width="150" />
        <el-table-column prop="position" label="岗位" width="150" />
      </el-table>
    </div>
    <el-pagination :current-page="page" :page-size="pageSize" :total="total" layout="prev, pager, next, total" @current-change="changePage" />
    
    <!-- 无搜索结果提示 -->
    <div v-if="hasSearched && searchResults.length === 0" class="no-results">
      <el-empty description="未找到匹配的人员" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import GoodSearchForm from './GoodSearchForm.vue'
import type { SearchFormData, GoodSearchConfig } from './type'
import type { PersonnelListItem } from '@/apis/common/type'
import { getPersonnelList } from '@/apis/advancedSettings/people'

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
const searchResults = ref<PersonnelListItem[]>([])

/**
 * 是否已搜索过
 */
const hasSearched = ref(false)
const loading = ref(false)
const error = ref('')
const page = ref(props.pagination?.pageIndex || 1)
const pageSize = props.pagination?.pageSize || 20
const total = ref(0)
let applied: Record<string, any> = {}
let sequence = 0

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
  showUser: false,
  showRemark: false,

  // 自定义字段
  customFields: [
    {
      key: 'peopleName',
      label: '请输入人员名称',
      type: 'input'
    },
    {
      key: 'peopleCode',
      label: '请输入人员编号',
      type: 'input'
    },
    {
      key: 'gender',
      label: '请选择人员性别',
      type: 'select',
      options: [
        { label: '男', value: '男' },
        { label: '女', value: '女' }
      ]
    },
    {
      key: 'contactPhone',
      label: '请输入联系电话',
      type: 'input'
    },
    {
      key: 'contactAddress',
      label: '请输入联系地址',
      type: 'input'
    },
    {
      key: 'idCard',
      label: '请输入身份证号',
      type: 'input'
    },
    {
      key: 'remark',
      label: '请输入备注信息',
      type: 'input'
    }
  ]
})

/**
 * 处理搜索事件
 */
function handleSearch(formData: SearchFormData) {
  applied = {
    name: formData.peopleName || undefined, number: formData.peopleCode || undefined,
    sex: formData.gender === '男' ? '1' : formData.gender === '女' ? '0' : undefined,
    tel: formData.contactPhone || undefined, add: formData.contactAddress || undefined,
    card: formData.idCard || undefined, data: formData.remark || undefined
  }
  page.value = 1
  void loadPeople()
}
function changePage(value: number) { page.value = value; void loadPeople() }
async function loadPeople() {
  const request = ++sequence
  loading.value = true; error.value = ''; hasSearched.value = true
  try {
    const result = await getPersonnelList({ pageIndex: page.value, pageSize, ...applied })
    if (request !== sequence) return
    if (result.code !== 10000 || !Array.isArray(result.data?.rows)) throw new Error(result.message || '人员列表读取失败')
    searchResults.value = result.data.rows.filter(row => row.id && row.name).map(row => ({
      id: String(row.id), name: row.name || '', employeeNo: row.number || '', deptId: row.frame,
      gender: Number(row.sex) === 1 ? '男' : Number(row.sex) === 0 ? '女' : '', phone: row.tel,
      address: row.add, idCard: row.card, remark: row.data
    }))
    total.value = Number(result.data.total) || 0
  } catch (error: any) {
    if (request !== sequence) return
    console.error('搜索人员失败:', error)
    searchResults.value = []; total.value = 0
    // Keep the error visible; a failed query must never emit a selected person.
    setError(error)
  } finally { if (request === sequence) loading.value = false }
}
function setError(cause: unknown) { error.value = cause instanceof Error ? cause.message : '搜索人员失败，请重试' }
onMounted(() => { void loadPeople() })

/**
 * 处理表格行点击事件（选择人员）
 */
function handleRowClick(row: PersonnelListItem) {
  emit('search', {
    ...row,
    id: row.id, // 传递人员ID
    name: row.name, // 保留name用于显示
    number: row.employeeNo
  })
  ElMessage.success(`已选择人员：${row.name}`)
}

// 暴露方法给父组件
defineExpose({
  getFormData: () => searchForm.value,
  resetSearch: () => {
    searchForm.value = {}
    handleSearch(searchForm.value)
  },
  triggerSearch: () => {
    handleSearch(searchForm.value)
  },
  searchForm
})
</script>

