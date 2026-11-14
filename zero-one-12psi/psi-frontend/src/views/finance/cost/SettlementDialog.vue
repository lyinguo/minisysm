<template>
  <el-dialog
    v-model="innerVisible"
    fullscreen
    :close-on-click-modal="false"
    class="sb-detail-dialog"
    title="结算"
  >
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="left">
        <!-- 供应商选择 -->
        <div class="form-item">
          <label class="form-label">供应商</label>
          <el-input
            v-model="formData.supplier"
            placeholder="请选择供应商"
            readonly
            clearable
            style="cursor: pointer; width: 240px"
            @focus="handleSupplierInputFocus"
            @clear="handleSupplierClear"
          >
            <template #suffix>
              <el-icon @click.stop="handleSupplierInputFocus" style="cursor: pointer">
                <Search />
              </el-icon>
            </template>
          </el-input>
        </div>

        <!-- 单据日期 -->
        <div class="form-item">
          <label class="form-label">单据日期</label>
          <el-date-picker
            v-model="header.documentDate"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            class="date-input"
          />
        </div>

        <!-- 单据编号 -->
        <div class="form-item">
          <label class="form-label">单据编号</label>
          <el-input
            v-model="header.documentNumber"
            placeholder="自动生成"
            clearable
            class="number-input"
          />
        </div>
      </div>
    </div>

    <!-- 分割线 -->
    <div class="divider"></div>

    <!-- 主体内容 -->
    <div class="main">
      <!-- 表格部分 -->
      <div class="table-wrap">
        <el-table :data="tableData" border highlight-current-row style="width: 100%">
          <!-- 第一列：设置按钮 + 序号 -->
          <el-table-column label="设置" width="70" align="center">
            <template #header>
              <el-button type="text" size="small" @click="showColumnSetting = true">
                <el-icon><Setting /></el-icon>
              </el-button>
            </template>
            <template #default="scope">
              {{ scope.$index + 1 }}
            </template>
          </el-table-column>

          <!-- 第二列：操作 -->
          <el-table-column label="操作" width="100" align="center">
            <template #default="scope">
              <el-button v-if="scope.$index === 0" type="text" size="small" @click="addNewRow">
                <el-icon><Plus /></el-icon>
              </el-button>
              <el-button v-else type="text" size="small" @click="deleteRow(scope.$index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>

          <!-- 支出类别 -->
          <el-table-column
            v-if="visibleColumns.expenseType"
            label="支出类别"
            align="center"
            width="150"
          >
            <template #default="scope">
              <el-select
                v-model="scope.row.expenseType"
                placeholder="点击选择"
                clearable
                @change="handleExpenseTypeChange(scope.row)"
              >
                <el-option label="采购支出" value="采购支出" />
                <el-option label="人力成本" value="人力成本" />
                <el-option label="租金支出" value="租金支出" />
                <el-option label="水电物业费" value="水电物业费" />
                <el-option label="运输物流费" value="运输物流费" />
              </el-select>
            </template>
          </el-table-column>

          <!-- 结算金额 -->
          <el-table-column
            v-if="visibleColumns.settlementAmount"
            label="结算金额"
            align="center"
            width="150"
          >
            <template #default="{ row }">
              <div
                contenteditable="true"
                class="editable-cell"
                @input="onEditableInput(row, 'settlementAmount', $event)"
                @blur="onEditableBlur(row, 'settlementAmount', $event)"
              >
                {{ row.settlementAmount || '' }}
              </div>
            </template>
          </el-table-column>

          <!-- 备注信息 -->
          <el-table-column v-if="visibleColumns.remark" label="备注信息" align="center">
            <template #default="{ row }">
              <div
                contenteditable="true"
                class="editable-cell"
                @input="onEditableInput(row, 'remark', $event)"
                @blur="onEditableBlur(row, 'remark', $event)"
              >
                {{ row.remark || '' }}
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 列显隐弹窗 -->
        <el-dialog v-model="showColumnSetting" title="列显示设置" width="360px">
          <el-checkbox-group v-model="checkedColumns">
            <el-checkbox v-for="(label, key) in columnLabels" :key="key" :label="key">
              {{ label }}
            </el-checkbox>
          </el-checkbox-group>
          <template #footer>
            <el-button @click="showColumnSetting = false">关闭</el-button>
          </template>
        </el-dialog>

        <!-- 状态栏 -->
        <div class="grid-status">
          <span class="status-item">总条数: {{ totalCount }}</span>
          <span class="status-item">总金额: {{ totalSum }}</span>
        </div>
      </div>

      <div class="divider"></div>

      <!-- 底部表单 -->
      <div class="document-form-container">
        <el-form
          :model="documentFormData"
          :rules="formRules"
          ref="documentFormRef"
          label-width="120px"
          inline
          class="bottom-form"
        >
          <!-- 单据金额 -->
          <el-form-item label="单据金额" prop="documentCost">
            <el-input
              v-model="documentFormData.documentCost"
              placeholder="单据金额"
              style="width: 200px"
              readonly
            />
          </el-form-item>

          <!-- 实际金额 -->
          <el-form-item label="实际金额" prop="actualAmount">
            <el-input
              v-model="documentFormData.actualAmount"
              placeholder="请输入实际金额"
              style="width: 200px"
            />
          </el-form-item>

          <!-- 实付金额 -->
          <el-form-item label="实付金额" prop="paidAmount">
            <el-input
              v-model="documentFormData.paidAmount"
              placeholder="请输入实付金额"
              style="width: 200px"
            />
          </el-form-item>

          <!-- 结算账户 -->
          <el-form-item label="结算账户" prop="settlementAccountId">
            <el-select
              v-model="documentFormData.settlementAccountId"
              filterable
              clearable
              placeholder="请选择结算账户"
              style="width: 280px"
              @change="handleAccountSelect"
            >
              <el-option
                v-for="item in accountList"
                :key="item.账户编号"
                :label="`${item.账户名称}（${item.所属组织 || '未分组'}）`"
                :value="item.账户编号"
              >
                <div class="option-row">
                  <span>{{ item.账户名称 }}</span>
                  <span class="option-meta">{{ item.所属组织 || '未分组' }} · 余额 {{ formatMoney(item.账户余额) }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <!-- 关联人员 -->
          <el-form-item label="关联人员" prop="relatedPersonId">
            <el-select
              v-model="documentFormData.relatedPersonId"
              filterable
              clearable
              placeholder="请选择关联人员"
              style="width: 280px"
              @change="handlePeopleSelect"
            >
              <el-option
                v-for="item in peopleList"
                :key="item.人员编号"
                :label="`${item.人员名称}（${item.所属组织 || '未分组'}）`"
                :value="item.人员编号"
              >
                <div class="option-row">
                  <span>{{ item.人员名称 }}</span>
                  <span class="option-meta">{{ item.所属组织 || '未分组' }}{{ item.联系电话 ? ` · ${item.联系电话}` : '' }}</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <!-- 单据附件 -->
          <el-form-item label="单据附件">
            <el-upload
              class="upload-demo"
              action="/api/upload"
              :on-preview="handlePreview"
              :on-remove="handleRemove"
              :before-remove="beforeRemove"
              :limit="3"
              :on-exceed="handleExceed"
              :file-list="fileList"
            >
              <el-button type="primary">点击上传</el-button>
              <template #tip>
                <div class="el-upload__tip">最多上传3个文件，且单个文件不超过5MB</div>
              </template>
            </el-upload>
          </el-form-item>

          <!-- 备注信息 -->
          <el-form-item label="备注信息">
            <el-input
              v-model="documentFormData.remarks"
              placeholder="备注信息"
              style="width: 200px"
              type="textarea"
              :rows="2"
            />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="innerVisible = false">关闭</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </div>
    </template>

    <!-- 供应商搜索弹窗 -->
    <el-dialog
      v-model="showSupplierDialog"
      title="供应商搜索"
      width="720px"
      append-to-body
      :close-on-click-modal="false"
    >
      <Supplier @search="handleSupplierDialogSearch" />
      <template #footer>
        <el-button @click="closeSupplierDialog">关闭</el-button>
      </template>
    </el-dialog>

  </el-dialog>
</template>

<script setup lang="ts">
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Setting, Delete, Plus } from '@element-plus/icons-vue'

// 导入搜索组件
import Supplier from '@/components/goodSearchConpoent/Supplier.vue'
import {
  loadAccountOptions,
  loadPeopleOptions,
  type AccountOption,
  type PeopleOption
} from '@/apis/finance/masterData'

// 导入类型定义
interface OtherExpenseTableRow {
  expenseType: string
  settlementAmount: string
  remark: string
}

interface DocumentFormFields {
  documentCost: string
  actualAmount: string
  paidAmount: string
  settlementAccountId: string
  settlementAccount: string
  relatedPersonId: string
  relatedPerson: string
  documentAttachment: string
  remarks: string
}

/* props & emits */
interface Props {
  visible: boolean
  selectedRecords?: any[]
}
const props = defineProps<Props>()
const emit = defineEmits(['update:visible', 'save', 'settlement-success'])

/* v-model:visible */
const innerVisible = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v)
})

/* 头部表单数据 */
const header = reactive({
  documentDate: new Date().toISOString().split('T')[0],
  documentNumber: `SE${new Date().getTime().toString().slice(-8)}` // 单据编号前缀改为SE（支出）
})

/* 供应商相关 */
const formData = reactive({
  supplier: ''
})

/* 表格数据 */
const tableData = ref<OtherExpenseTableRow[]>([
  {
    expenseType: '', // 改为支出类别
    settlementAmount: '',
    remark: ''
  }
])

/* 底部表单数据 */
const documentFormData = reactive<DocumentFormFields>({
  documentCost: '',
  actualAmount: '',
  paidAmount: '', // 实付金额
  settlementAccountId: '',
  settlementAccount: '',
  relatedPersonId: '',
  relatedPerson: '',
  documentAttachment: '',
  remarks: ''
})

const accountList = ref<AccountOption[]>([])
const peopleList = ref<PeopleOption[]>([])

async function loadMasterData() {
  try {
    const [accounts, people] = await Promise.all([loadAccountOptions(), loadPeopleOptions()])
    accountList.value = accounts
    peopleList.value = people
    if (!accounts.length || !people.length) {
      ElMessage.warning('结算账户或关联人员资料为空，请先在基础资料中维护')
    }
  } catch (error) {
    console.error('loadMasterData failed', error)
    ElMessage.warning('基础资料加载失败，请刷新重试')
  }
}

const formatMoney = (value: number) => {
  return Number(value || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const handleAccountSelect = (accountId: string) => {
  const account = accountList.value.find((item) => item.账户编号 === accountId)
  documentFormData.settlementAccountId = accountId || ''
  documentFormData.settlementAccount = account?.账户名称 || ''
}

const handlePeopleSelect = (peopleId: string) => {
  const person = peopleList.value.find((item) => item.人员编号 === peopleId)
  documentFormData.relatedPersonId = peopleId || ''
  documentFormData.relatedPerson = person?.人员名称 || ''
}

// 表单引用
const documentFormRef = ref()

// 表单验证规则 - 实付金额设为必填
const formRules = {
  actualAmount: [
    { required: true, message: '请输入实际金额', trigger: 'blur' },
    { pattern: /^\d+(\.\d{1,2})?$/, message: '请输入正确的金额格式', trigger: 'blur' }
  ],
  paidAmount: [
    { required: true, message: '请输入实付金额', trigger: 'blur' },
    { pattern: /^\d+(\.\d{1,2})?$/, message: '请输入正确的金额格式', trigger: 'blur' }
  ],
  settlementAccountId: [{ required: true, message: '请选择结算账户', trigger: 'change' }],
  relatedPersonId: [{ required: true, message: '请选择关联人员', trigger: 'change' }]
}

// 文件上传相关
const fileList = ref([])

const handleRemove = (file: any, uploadFiles: any) => {
  console.log(file, uploadFiles)
}

const handlePreview = (uploadFile: any) => {
  console.log(uploadFile)
}

const handleExceed = (files: any, uploadFiles: any) => {
  ElMessage.warning(
    `当前限制选择 3 个文件，本次选择了 ${files.length} 个文件，共选择了 ${files.length + uploadFiles.length} 个文件`
  )
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const beforeRemove = (uploadFile: any, uploadFiles: any) => {
  return ElMessageBox.confirm(`确定移除 ${uploadFile.name}？`).then(
    () => true,
    () => false
  )
}

// ====== 弹窗控制 ======
const showSupplierDialog = ref(false)
const isClosingDialog = ref(false)

/** 处理供应商输入框获得焦点 */
function handleSupplierInputFocus() {
  if (isClosingDialog.value) return
  showSupplierDialog.value = true
}

/** 关闭供应商弹窗 */
function closeSupplierDialog() {
  isClosingDialog.value = true
  showSupplierDialog.value = false
  setTimeout(() => {
    isClosingDialog.value = false
  }, 300)
}

/** 处理供应商清空 */
function handleSupplierClear() {
  formData.supplier = ''
}

/** 处理供应商弹窗内的搜索 */
function handleSupplierDialogSearch(params: any) {
  if (params && typeof params === 'object') {
    const name = params.name || params.supplierName || ''
    formData.supplier = name
    ElMessage.success(`已选择供应商：${name}`)
  }
  closeSupplierDialog()
}

// ====== 表格操作 ======
function addNewRow() {
  tableData.value.push({
    expenseType: '',
    settlementAmount: '',
    remark: ''
  })
}

function deleteRow(index: number) {
  if (tableData.value.length > 1) {
    tableData.value.splice(index, 1)
    ElMessage.success('已删除该行')
    recalculateTotals()
  } else {
    ElMessage.warning('至少保留一行数据')
  }
}

function handleExpenseTypeChange(row: OtherExpenseTableRow) {
  console.log('支出类别选择:', row.expenseType)
  recalculateTotals()
}

// ====== 可编辑单元格 ======
type EditableField = 'settlementAmount' | 'remark'

function onEditableInput(row: OtherExpenseTableRow, field: EditableField, e: Event) {
  const el = e.target as HTMLElement | null
  if (!el) return

  const raw = el.innerText ?? ''

  if (field === 'remark') {
    row.remark = raw
    return
  }

  // 数值字段：清洗为数字/小数
  const cleaned = raw.replace(/[^\d.]/g, '')
  row[field] = cleaned
  recalculateTotals()
}

function onEditableBlur(row: OtherExpenseTableRow, field: EditableField, e: Event) {
  const el = e.target as HTMLElement | null
  if (!el) return
  const text = el.innerText ?? ''

  if (field === 'remark') {
    row.remark = text
    return
  }

  const num = parseFloat(text)
  // 失焦时把值规整为数值或空
  row[field] = Number.isFinite(num) ? String(num) : ''
  recalculateTotals()
}

// ====== 计算和状态 ======
const totalCount = computed(() => tableData.value.length)

const totalSum = computed(() => {
  return tableData.value.reduce((sum, r) => sum + (Number(r.settlementAmount) || 0), 0).toFixed(2)
})

function recalculateTotals() {
  const totalAmount = tableData.value.reduce((sum, row) => {
    return sum + (parseFloat(row.settlementAmount) || 0)
  }, 0)

  documentFormData.documentCost = totalAmount.toFixed(2)

  // 如果实际金额和实付金额为空，自动填充
  if (!documentFormData.actualAmount) {
    documentFormData.actualAmount = totalAmount.toFixed(2)
  }
  if (!documentFormData.paidAmount) {
    documentFormData.paidAmount = totalAmount.toFixed(2)
  }
}

// ====== 列显隐设置 ======
const showColumnSetting = ref(false)
const columnLabels: Record<string, string> = {
  expenseType: '支出类别', // 改为支出类别
  settlementAmount: '结算金额',
  remark: '备注信息'
}
const checkedColumns = ref<string[]>(Object.keys(columnLabels))
const visibleColumns = reactive<Record<string, boolean>>({})

watch(
  checkedColumns,
  (val) => {
    for (const k in columnLabels) visibleColumns[k] = val.includes(k)
  },
  { immediate: true }
)

// ====== 按钮功能 ======
/* 保存 */
const save = async () => {
  // 验证表单
  if (!documentFormRef.value) return

  const valid = await documentFormRef.value.validate().catch(() => false)
  if (!valid) {
    ElMessage.error('请完善必填信息')
    return
  }

  // 构建结算数据
  const settlementData = {
    header,
    supplier: formData.supplier,
    tableData: tableData.value,
    footer: documentFormData
  }

  // 发送结算成功事件
  emit('settlement-success', settlementData)
  emit('save', settlementData)

  ElMessage.success('结算成功')
  innerVisible.value = false
}

// 监听选中的记录变化，填充数据
watch(
  () => props.selectedRecords,
  (newRecords) => {
    if (newRecords && newRecords.length > 0) {
      // 填充供应商信息（使用第一个记录的往来单位）
      if (newRecords[0].contactUnit) {
        formData.supplier = newRecords[0].contactUnit
      }

      // 填充表格数据
      tableData.value = newRecords.map((record) => ({
        expenseType: record.expenseType || '采购支出',
        settlementAmount: Math.abs(record.unsettledAmount).toString(),
        remark: `结算单据：${record.orderNo}`
      }))

      // 重新计算金额
      recalculateTotals()
    }
  },
  { immediate: true }
)

watch(innerVisible, (visible) => {
  if (visible) {
    loadMasterData()
  }
})

onMounted(() => {
  recalculateTotals()
  loadMasterData()
})
</script>

<style scoped>
/* 按钮图标黑白化风格 */
:deep(.el-button) {
  color: #333;
}

:deep(.el-button:hover) {
  color: #000;
  background-color: #f5f5f5;
}

:deep(.el-icon svg) {
  width: 16px;
  height: 16px;
  fill: currentColor;
}

:deep(.el-button.is-text.el-button--danger) {
  color: #333;
}
:deep(.el-button.is-text.el-button--danger:hover) {
  color: #000;
  background-color: #f5f5f5;
}
:deep(.el-button.is-text) {
  border: none;
  box-shadow: none;
  padding: 4px;
  color: #444;
}

:deep(.el-button.is-text:hover) {
  background-color: #eee;
}

/* ===== 弹窗整体布局 ===== */
.sb-detail-dialog :deep(.el-dialog__body) {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 0 16px;
  box-sizing: border-box;
}

/* 顶部工具栏固定 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  flex-shrink: 0;
  border-bottom: 1px solid #ebeef5;
}
.toolbar .left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  color: #606266;
  font-weight: 500;
  white-space: nowrap;
}

.date-input {
  width: 160px;
}

.number-input {
  width: 180px;
}

.ml8 {
  margin-left: 8px;
}

/* 分割线 */
.divider {
  border-top: 1px solid #ebeef5;
}

/* 主体部分 */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}

/* 表格区域 */
.table-wrap {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-bottom: 1px solid #ebeef5;
  position: relative;
}

.table-wrap :deep(.el-table) {
  flex: 1;
  overflow-y: auto;
  min-height: 300px;
}

/* 状态栏 */
.grid-status {
  flex-shrink: 0;
  border-top: 1px solid #ebeef5;
  background: #fafafa;
  text-align: left;
  padding: 6px 16px;
  font-size: 13px;
  color: #606266;
  display: flex;
  gap: 20px;
}

.status-item {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

/* 底部表单 */
.document-form-container {
  flex-shrink: 0;
  border-top: 1px solid #ebeef5;
  padding: 12px 16px;
  background: #f9fafb;
}

.bottom-form {
  margin-bottom: 0;
}

.upload-demo {
  width: 200px;
}

/* 可编辑单元格 */
.editable-cell {
  min-height: 32px;
  line-height: 32px;
  text-align: center;
  border: none;
  outline: none;
  background-color: transparent;
  padding: 0;
  font-size: 14px;
  color: #303133;
  cursor: text;
}

:deep(.el-select) {
  width: 100%;
}

/* 底部按钮 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  padding: 10px 0;
  gap: 10px;
}

.option-row {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  padding: 2px 0;
}

.option-meta {
  font-size: 12px;
  color: #909399;
}
</style>
