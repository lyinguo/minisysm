<!--
 * @Author: f1-duanhong 1271736670@qq.com
 * @Date: 2025-10-25 13:25:14
 * @LastEditors: f1-duanhong 1271736670@qq.com
 * @LastEditTime: 2025-11-10 19:48:36
 * @FilePath: \psi-frontend\src\views\sysmanage\import\Index.vue
 * @Description: 系统配置-导入模板主页面
-->
<template>
  <div class="menu area">
    <el-alert
      title="这里管理 Excel 模板文件；导入业务数据，请进入对应业务页面。"
      type="info"
      :closable="false"
      show-icon
      class="template-notice"
    />
    <el-collapse v-model="helpPanels" class="template-help">
      <el-collapse-item title="第一次使用：模板是什么？怎样导入数据？" name="usage">
        <p>模板是一份预先设置好列名和格式的 Excel 表格，例如供应商模板会规定供应商名称、编号等字段。它让系统知道每列数据代表什么。</p>
        <ol>
          <li>进入需要导入数据的业务页面，找到“下载模板”（有些页面在“批量操作”里）。优先使用该业务页面提供的模板。</li>
          <li>用 Excel 或 WPS 打开下载的文件，按说明填写必填项；保留原来的列名、工作表和格式，不要直接拿其他模块的模板套用。</li>
          <li>保存填写后的文件，回到同一个业务页面，点击“导入”并选择文件。首次可先填一条测试记录，导入后检查列表结果。</li>
        </ol>
        <p>若管理员已在本页保存了对应模板，可点击该行“详情 → 下载文件”。本页的“新增”只登记模板文件，不会导入其中的业务记录，也不会自动改变其他模块的导入规则。</p>
        <div class="business-links">
          <el-button @click="router.push('/supplier-manage')">去供应商管理</el-button>
          <el-button @click="router.push('/customer-manage')">去客户管理</el-button>
          <el-button @click="router.push('/product-manage')">去商品管理</el-button>
        </div>
      </el-collapse-item>
      <el-collapse-item title="管理员：如何新增和维护模板？" name="management">
        <ol>
          <li>先从对应业务模块获取正确模板，保留空白格式及填写说明，不要上传包含真实客户或业务记录的文件。</li>
          <li>点击“新增”，选择 .xls 或 .xlsx 文件，填写易辨认的名称，如“供应商导入模板”。存储方式通常保持默认 local（本地存储）。</li>
          <li>在备注中写明适用模块、必填字段和填写要求，再点击“添加”。如状态显示“未使用”，可通过“编辑”将其改为“使用中”。</li>
          <li>通过“详情 → 下载文件”检查上传结果。若历史模板提示旧存储不可用，需要重新上传正确文件后再下载。</li>
        </ol>
      </el-collapse-item>
    </el-collapse>
    <div class="layout">
      <SearchPopover v-model="searchFrom" @search="handleSearch(1)" />
      <el-button-group>
        <el-button @click="handleAdd">新增</el-button>
        <el-button @click="handleReload">刷新</el-button>
      </el-button-group>
    </div>
    <el-divider />

    <NormalTable
      :tabdatacolumns="tableColumns"
      :tabdata="tablePageData"
      :taboperbtns="tableOperBtns"
      @update:tabdata="handlePageChange"
      @taboper-click="handleTableOperClick"
    >
      <!-- 自定义操作列插槽 -->
      <template #customercell="{ column, prop, row }">
        <template v-if="prop === 'operate'">
          <el-button-group>
            <el-button @click="handleDetail(row.id)" size="small">详情</el-button>
            <el-button @click="handleEdit(row.id)" size="small">编辑</el-button>
            <el-button
              @click="handleToggleStatus(row)"
              :style="row.status === 1 ? 'color: #F56C6C;' : 'color: #67C23A;'"
              size="small"
              plain
            >
              {{ row.status === 1 ? '停用' : '启用' }}
            </el-button>
            <el-button @click="handleDelete(row.id)" size="small">删除</el-button>
          </el-button-group>
        </template>
        <template v-else-if="prop === 'saveType'">
          {{ getStorageTypeText(row.saveType) }}
        </template>
        <template v-else-if="prop === 'status'">
          <el-tag :type="row.status === 1 ? 'success' : 'info'">
            {{ getDataStatusText(row.status) }}
          </el-tag>
        </template>
        <template v-else>
          {{ row[prop] }}
        </template>
      </template>
    </NormalTable>

    <!-- 新增/编辑弹窗 -->
    <CreateDialog
      v-model:visible="createDialogVisible"
      :form-data="currentFormData"
      :mode="dialogMode"
      @save="handleSave"
      @cancel="handleDialogCancel"
    />

    <!-- 详情弹窗 -->
    <DetailDialog
      v-model:visible="detailDialogVisible"
      :form-data="currentDetailData"
      @close="handleDetailClose"
    />
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import NormalTable from '@/components/normaltable/NormalTable.vue'
import type { MyTableColumn, MyTableOperationsBtn, PageDTO } from '@/components/normaltable/type'
import CreateDialog from './CreateDialog.vue'
import DetailDialog from './DetailDialog.vue'
import SearchPopover from './SearchPopover.vue'
import {
  getTemplateList,
  getTemplateDetail,
  importTemplate,
  updateTemplate,
  deleteTemplate
} from '@/apis/sysmanage/import/index'
import type { PageRequest, ImportTemplateList } from '@/apis/sysmanage/import/type'

// 响应式数据
const router = useRouter()
const helpPanels = ref<string[]>(['usage'])
const createDialogVisible = ref(false) // 新增/编辑弹窗显示状态
const detailDialogVisible = ref(false) // 详情弹窗显示状态
const dialogMode = ref<'add' | 'edit'>('add')
const currentFormData = ref<ImportTemplateList>() // 当前编辑的表单数据
const currentDetailData = ref<ImportTemplateList>() // 当前详情的表单数据

// 搜索表单 - 根据接口字段结构调整
const searchFrom = ref<PageRequest>({
  templateName: '',
  saveType: '',
  status: undefined
})

// 表格分页数据
const tablePageData = ref<PageDTO<ImportTemplateList>>({
  rows: [],
  total: 0,
  pageIndex: 1,
  pageSize: 30
})

// 表格列配置 - 使用接口字段名
const tableColumns = ref<MyTableColumn[]>([
  { prop: 'templateName', label: '模板名称', 'min-width': '120px', align: 'center' },
  { prop: 'saveType', label: '存储方式', 'min-width': '120px', align: 'center' },
  { prop: 'status', label: '数据状态', 'min-width': '120px', align: 'center' },
  { prop: 'operate', label: '操作', 'min-width': '220px', align: 'center' }
])

// 表格操作按钮配置
const tableOperBtns = ref<MyTableOperationsBtn[]>([
  { text: '详情', evtname: 'detail', attr: { size: 'small', type: 'primary' } },
  { text: '编辑', evtname: 'edit', attr: { size: 'small', type: 'primary' } },
  { text: '删除', evtname: 'delete', attr: { size: 'small', type: 'danger' } }
])

// 方法
const fetchMenuData = async () => {
  const params: PageRequest = {
    ...searchFrom.value,
    pageIndex: tablePageData.value.pageIndex,
    pageSize: tablePageData.value.pageSize
  }

  getTemplateList(
    params,
    (data) => {
      tablePageData.value.rows = data.rows || []
      tablePageData.value.total = data.total || 0
    },
    (error) => {
      ElMessage.error('获取数据失败: ' + (error as Error).message)
    }
  )
}

// 获取模板详情
const fetchTemplateDetail = async (id: string): Promise<ImportTemplateList | null> => {
  return new Promise((resolve) => {
    getTemplateDetail(
      id,
      (data) => {
        resolve(data)
      },
      (error) => {
        ElMessage.error('获取模板详情失败: ' + (error as Error).message)
        resolve(null)
      }
    )
  })
}

// 搜索方法
const handleSearch = (currentPage?: number): void => {
  if (currentPage) {
    tablePageData.value.pageIndex = currentPage
  }
  fetchMenuData()
}

// NormalTable 分页变化处理
const handlePageChange = (data: PageDTO<ImportTemplateList>): void => {
  tablePageData.value = data
  fetchMenuData()
}

// NormalTable 操作按钮点击处理
const handleTableOperClick = (index: number, row: ImportTemplateList, evtname: string): void => {
  switch (evtname) {
    case 'detail':
      handleDetail(row.id)
      break
    case 'edit':
      handleEdit(row.id)
      break
    case 'delete':
      handleDelete(row.id)
      break
    default:
      console.warn('未知的操作类型:', evtname)
  }
}

// 存储方式文本转换
const getStorageTypeText = (saveType: string): string => {
  const storageTypeMap: { [key: string]: string } = {
    local: '本地存储',
    cloud: '云存储',
    database: '数据库存储',
    filesystem: '文件系统'
  }
  return storageTypeMap[saveType] || saveType || '未知'
}

// 数据状态文本转换
const getDataStatusText = (status: number): string => {
  const dataStatusMap: { [key: number]: string } = {
    0: '未使用',
    1: '使用中'
  }
  return dataStatusMap[status] || '未知'
}

// 启用/停用模板 - 直接构建 FormData
const handleToggleStatus = (row: ImportTemplateList) => {
  if (!row.id) return
  const newStatus = row.status === 1 ? 0 : 1
  const confirmText = newStatus === 1 ? '启用' : '停用'

  ElMessageBox.confirm(`确定要${confirmText}该模板吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    if (!row.id) return
    // 直接构建 FormData
    const formData = new FormData()
    formData.append('status', newStatus.toString())

    updateTemplate(
      row.id,
      formData,
      () => {
        ElMessage.success(`${confirmText}成功`)
        fetchMenuData()
      },
      (error) => {
        ElMessage.error(`${confirmText}失败: ${(error as Error).message}`)
      }
    )
  })
}

// 新增模板
const handleAdd = (): void => {
  dialogMode.value = 'add'
  currentFormData.value = undefined
  createDialogVisible.value = true
}

// 编辑模板
const handleEdit = async (id?: string): Promise<void> => {
  if (!id) {
    ElMessage.warning('模板ID不存在')
    return
  }

  try {
    const templateDetail = await fetchTemplateDetail(id)

    if (templateDetail) {
      dialogMode.value = 'edit'
      currentFormData.value = { ...templateDetail }
      createDialogVisible.value = true
    } else {
      ElMessage.warning('未找到模板信息')
    }
  } catch (error) {
    ElMessage.error('加载模板信息失败')
    console.error('Error loading template detail:', error)
  }
}

// 查看详情
const handleDetail = async (id?: string): Promise<void> => {
  if (!id) {
    ElMessage.warning('模板ID不存在')
    return
  }

  try {
    const templateDetail = await fetchTemplateDetail(id)

    if (templateDetail) {
      currentDetailData.value = { ...templateDetail }
      detailDialogVisible.value = true
    } else {
      ElMessage.warning('未找到模板信息')
    }
  } catch (error) {
    ElMessage.error('加载模板详情失败')
    console.error('Error loading template detail:', error)
  }
}

// 详情弹窗关闭处理
const handleDetailClose = (): void => {
  detailDialogVisible.value = false
  currentDetailData.value = undefined
}

const buildFormData = (formData: any, includeFile: boolean = true): FormData => {
  const submitFormData = new FormData()

  // 添加文件（如果存在且需要包含文件）
  if (includeFile && formData.file) {
    if (formData.file.raw) {
      submitFormData.append('file', formData.file.raw)
    } else if (formData.file instanceof File) {
      submitFormData.append('file', formData.file)
    }
  }

  // 添加其他字段
  if (formData.templateName) {
    submitFormData.append('templateName', formData.templateName)
  }
  if (formData.saveType) {
    submitFormData.append('saveType', formData.saveType)
  }
  if (formData.status !== undefined) {
    submitFormData.append('status', formData.status.toString())
  }
  if (formData.remark) {
    submitFormData.append('remark', formData.remark)
  }
  if (formData.templateCode) {
    submitFormData.append('templateCode', formData.templateCode)
  }

  // 调试：查看 FormData 内容
  console.log('构建的 FormData 内容:')
  const entries = Array.from((submitFormData as any).entries() as Iterable<[string, any]>)
  for (const [key, value] of entries) {
    console.log(`${key}:`, value)
  }

  return submitFormData
}

const handleSave = (formData: any) => {
  // 调试信息，查看传递的数据
  console.log('接收到的表单数据:', formData)

  // 使用通用的构建函数创建 FormData
  const submitFormData = buildFormData(formData)

  if (dialogMode.value === 'add') {
    // 新增模板
    importTemplate(
      submitFormData,
      () => {
        createDialogVisible.value = false
        ElMessage.success('新增成功')
        fetchMenuData()
      },
      (error) => {
        ElMessage.error('新增失败: ' + (error as Error).message)
      }
    )
  } else if (dialogMode.value === 'edit' && formData.id) {
    // 编辑模板 - 添加 ID 到路径中
    updateTemplate(
      formData.id,
      submitFormData,
      () => {
        createDialogVisible.value = false
        ElMessage.success('编辑成功')
        fetchMenuData()
      },
      (error) => {
        ElMessage.error('编辑失败: ' + (error as Error).message)
      }
    )
  }
}

const handleDelete = (id?: string) => {
  if (!id) return
  ElMessageBox.confirm('确定要删除该模板吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    deleteTemplate(
      id,
      () => {
        ElMessage.success('删除成功')
        fetchMenuData()
      },
      (error) => {
        ElMessage.error('删除失败: ' + (error as Error).message)
      }
    )
  })
}

const handleReload = () => {
  fetchMenuData()
  ElMessage.success('刷新成功')
}

const handleDialogCancel = (): void => {
  createDialogVisible.value = false
  currentFormData.value = undefined
}

// 生命周期
onMounted(() => {
  fetchMenuData()
})
</script>

<style scoped>
.template-notice { margin-bottom: 12px; }
.template-help { margin-bottom: 18px; }
.template-help p, .template-help li { line-height: 1.8; }
.template-help li { margin-bottom: 6px; }
.business-links { display: flex; flex-wrap: wrap; gap: 8px; }
.business-links .el-button { margin-left: 0; }
.layout {
  display: flex;
  justify-content: space-between;
}
</style>
