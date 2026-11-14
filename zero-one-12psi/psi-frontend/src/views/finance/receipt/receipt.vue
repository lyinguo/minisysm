<template>
    <div class="imy bill">
      <el-form
        :model="form"
        :rules="rules"
        ref="formRef"
        :inline="true"
        :hide-required-asterisk="true"
        style="height: 100%"
      >
        <!-- 客户选择 -->
        <el-form-item label="客户" prop="customer">
          <template #label>
            <span>客户</span>
          </template>
          <div class="search-select-container">
            <el-input
              v-model="form.customerName"
              placeholder="请选择客户"
              readonly
              style="width: 200px"
            ></el-input>
            <el-button type="primary" @click="openCustomerDialog" style="margin-left: 8px">
              选择
            </el-button>
          </div>
        </el-form-item>
  
        <el-form-item label="单据日期" prop="time">
          <el-date-picker
            v-model="form.time"
            value-format="YYYY-MM-DD"
            type="date"
            placeholder="请选择单据日期"
          ></el-date-picker>
        </el-form-item>
  
        <el-form-item label="单据编号" prop="number">
          <el-input
            placeholder="请输入单据编号"
            v-model="form.number"
            clearable
          ></el-input>
        </el-form-item>
  
        <el-divider class="fistDivider"></el-divider>
  
        <!-- AG Grid 表格区域 -->
        <div class="table-container">
          <div class="table-header">
            <div class="table-title">结算信息</div>
            <div class="table-actions">
              <el-button type="primary" @click="addGridRow" size="small">
                新增
              </el-button>
            </div>
          </div>
          <div class="settlement-table-container">
            <el-table
              :data="tableData"
              :key="tableKey"
              style="width: 100%"
              :show-header="true"
              border
              size="small"
            >
              <!-- 序号列 + 齿轮配置按钮 -->
              <el-table-column type="index" width="60" align="center">
                <template #header>
                  <span class="th-gear" @click="configVisible = true">⚙</span>
                </template>
              </el-table-column>
              <el-table-column 
                label="操作" 
                width="80" 
                align="center"
              >
                <template #default="{ row, $index }">
                  <!-- 修改：只有第一行显示加号，其他行显示删除图标 -->
                  <el-button 
                    v-if="$index === 0" 
                    type="primary" 
                    size="small" 
                    @click="addRowAt($index)" 
                    class="add-row-btn"
                  >
                    +
                  </el-button>
                  <el-button 
                    v-else 
                    type="danger" 
                    size="small" 
                    @click="removeRow($index)" 
                    class="del-row-btn"
                  >
                    🗑
                  </el-button>
                </template>
              </el-table-column>
              
              <el-table-column 
                v-if="columnVisibles.account"
                label="结算账户" 
                prop="account" 
                min-width="220"
              >
                <template #default="{ row }">
                  <el-select
                    v-model="row.accountId"
                    filterable
                    clearable
                    placeholder="请选择结算账户"
                    size="small"
                    style="width: 100%"
                    @change="(val: string) => handleAccountSelect(row, val)"
                  >
                    <el-option
                      v-for="item in accountList"
                      :key="item.账户编号"
                      :label="`${item.账户名称}（${item.所属组织}）`"
                      :value="item.账户编号"
                    />
                  </el-select>
                </template>
              </el-table-column>
              
              <el-table-column 
                v-if="columnVisibles.amount"
                label="结算金额" 
                prop="money" 
                width="150"
                align="right"
              >
                <template #default="{ row }">
                  <el-input
                    v-model="row.money"
                    placeholder="0.00"
                    size="small"
                    @input="handleMoneyInput(row)"
                    @blur="formatMoney(row)"
                  />
                </template>
              </el-table-column>
              
              <el-table-column 
                v-if="columnVisibles.number"
                label="结算号" 
                prop="settle" 
                width="150"
              >
                <template #default="{ row }">
                  <el-input
                    v-model="row.settle"
                    placeholder=""
                    size="small"
                  />
                </template>
              </el-table-column>
              
              <el-table-column 
                v-if="columnVisibles.remark"
                label="备注信息" 
                prop="data" 
                min-width="200"
              >
                <template #default="{ row }">
                  <el-input
                    v-model="row.data"
                    placeholder=""
                    size="small"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
  
          <div class="table-footer">
            <div class="footer-info">
              <span>总条数{{ totalCount }} | 总金额{{ totalAmount }}</span>
            </div>
          </div>
          <!-- 字段配置弹窗 -->
          <el-dialog v-model="configVisible" title="字段配置" width="520px">
            <el-table :data="fieldConfig" border>
              <el-table-column prop="label" label="名称" />
              <el-table-column label="显示" width="160" align="center">
                <template #default="{ row }">
                  <el-switch :model-value="columnVisibles[row.key as keyof typeof columnVisibles]" @update:model-value="(val)=>setColumnVisible(row.key, val)" />
                </template>
              </el-table-column>
            </el-table>
          </el-dialog>
        </div>
  
        <el-divider></el-divider>
  
        <!-- 底部表单区域 -->
        <LineFeed tag=".el-form-item" :rule="3">
          <el-form-item label="单据金额">
            <el-input
              placeholder="请输入单据金额"
              v-model="form.total"
              :disabled="true"
            ></el-input>
          </el-form-item>
  
          <el-form-item label="关联人员">
            <el-select
              v-model="form.people"
              filterable
              clearable
              placeholder="请选择关联人员"
              style="width: 260px"
              @change="handlePeopleSelect"
            >
              <el-option
                v-for="item in peopleList"
                :key="item.人员编号"
                :label="`${item.人员名称}（${item.所属组织}）`"
                :value="item.人员编号"
              />
            </el-select>
          </el-form-item>
  
          <el-form-item label="单据附件">
            <NodUpload
              v-model="uploadFiles"
              :action="uploadAction"
            ></NodUpload>
          </el-form-item>
  
          <FieldForm
            style="display: initial"
            v-model="form.more"
            rule="imy"
            prefix="more."
          ></FieldForm>
  
          <el-form-item label="备注信息">
            <el-input
              placeholder="请输入备注信息"
              v-model="form.data"
              clearable
            ></el-input>
          </el-form-item>
        </LineFeed>
      </el-form>
  
      <!-- 客户选择对话框 -->
      <el-dialog
        v-model="customerDialogVisible"
        title="选择客户"
        width="80%"
      >
        <div class="dialog-content">
          <el-table
            :data="customerList"
            style="width: 100%"
            @selection-change="handleCustomerSelection"
            ref="customerTableRef"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="客户名称" label="客户名称" />
            <el-table-column prop="客户编号" label="客户编号" />
            <el-table-column prop="客户类别" label="客户类别" />
            <el-table-column prop="客户等级" label="客户等级" />
            <el-table-column prop="所属组织" label="所属组织" />
            <el-table-column prop="备注信息" label="备注信息" />
          </el-table>
        </div>
        <template #footer>
          <el-button @click="customerDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmCustomer">确定</el-button>
        </template>
      </el-dialog>
  
      <!-- 人员选择对话框 -->
      <el-dialog
        v-model="peopleDialogVisible"
        title="选择关联人员"
        width="80%"
      >
        <div class="dialog-content">
          <el-table
            :data="peopleList"
            style="width: 100%"
            @selection-change="handlePeopleSelection"
            ref="peopleTableRef"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="人员名称" label="人员名称" />
            <el-table-column prop="人员编号" label="人员编号" />
            <el-table-column prop="所属组织" label="所属组织" />
            <el-table-column prop="人员性别" label="性别" />
            <el-table-column prop="联系电话" label="联系电话" />
          </el-table>
        </div>
        <template #footer>
          <el-button @click="peopleDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmPeople">确定</el-button>
        </template>
      </el-dialog>
  
      <!-- 结算账户选择对话框 -->
      <el-dialog
        v-model="accountSelectionVisible"
        title="选择结算账户"
        width="80%"
      >
        <div class="dialog-content">
          <el-table
            :data="accountList"
            style="width: 100%"
            @selection-change="handleAccountSelection"
            ref="accountTableRef"
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="账户名称" label="账户名称" />
            <el-table-column prop="账户编号" label="账户编号" />
            <el-table-column prop="所属组织" label="所属组织" />
            <el-table-column prop="账户余额" label="账户余额">
              <template #default="{ row }">
                {{ formatCurrency(row.账户余额) }}
              </template>
            </el-table-column>
            <el-table-column prop="备注信息" label="备注信息" />
          </el-table>
        </div>
        <template #footer>
          <el-button @click="accountSelectionVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmAccount">确定</el-button>
        </template>
      </el-dialog>
  
      <div class="layerBtn">
        <el-button-group>
          <template v-if="form.id == 0 || (form.examine == 0 && hasEditPermission)">
            <el-button type="primary" @click="save">保存</el-button>
          </template>
          <template v-if="form.id != 0">
            <template v-if="hasExaminePermission">
              <el-button type="primary" @click="examine">
                {{ form.examine == 0 ? "审核" : "反审核" }}
              </el-button>
            </template>
          </template>
          <template v-if="source == null">
            <el-button type="info" @click="reload">刷新</el-button>
          </template>
        </el-button-group>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref, reactive, computed, onMounted, nextTick } from 'vue'
  import { useRouter } from 'vue-router'
  import { ElMessage, type ElTable } from 'element-plus'
  import { ReceiptAPI } from '@/apis/finance'
  import { toDateTime, toFileField } from '@/apis/finance/payload'
  import { useUserStore } from '@/stores/user'
  import {
    loadCustomerOptions,
    loadAccountOptions,
    loadPeopleOptions
  } from '@/apis/finance/masterData'
  
  // 导入组件
  import LineFeed from '@/components/lib/LineFeed.vue'
  import NodUpload from '@/components/lib/NodUpload.vue'
  import FieldForm from '@/components/lib/FieldForm.vue'
  
  // 工具函数
  const router = useRouter()
  const generateUniqid = () => {
    return Date.now().toString(36) + Math.random().toString(36).substr(2)
  }
  
  // 组件属性
  const props = defineProps({
    source: {
      default: null,
    }
  })
  
  // 表单引用
  const formRef = ref()
  const customerTableRef = ref<InstanceType<typeof ElTable>>()
  const peopleTableRef = ref<InstanceType<typeof ElTable>>()
  const accountTableRef = ref<InstanceType<typeof ElTable>>()
  
  // 定义表单数据的接口
  interface FormData {
    id: number;
    customer: string | null;
    customerName: string;
    time: string;
    number: string;
    total: number;
    people: string | null;
    peopleName: string;
    file: any[];
    data: string;
    examine: number;
    more: Record<string, any>;
  }
  
  // 表单数据 
  const form = reactive<FormData>({
    id: 0,
    customer: null,
    customerName: '',
    time: '',
    number: '',
    total: 0,
    people: null,
    peopleName: '',
    file: [],
    data: '',
    examine: 0,
    more: {},
  })

  // 附件上传（与 NodUpload 绑定的安全本地值，避免外部数据结构不一致导致渲染异常）
  const uploadFiles = ref<any[]>([])
  
  // 表格数据
  const tableData = ref<any[]>([])
  const tableKey = ref(0)
  // 字段配置
  const configVisible = ref(false)
  const columnVisibles = reactive({
    account: true,
    amount: true,
    number: true,
    remark: true
  })
  const fieldConfig = [
    { key: 'account', label: '结算账户' },
    { key: 'amount', label: '结算金额' },
    { key: 'number', label: '结算号' },
    { key: 'remark', label: '备注信息' }
  ]

  const setColumnVisible = (key: string, val: any) => {
    (columnVisibles as any)[key] = Boolean(val)
    tableKey.value++
  }
  
  // 对话框控制
  const customerDialogVisible = ref(false)
  const peopleDialogVisible = ref(false)
  const accountSelectionVisible = ref(false)
  
  // 当前选中的项
  const currentCustomer = ref<any[]>([])
  const currentPeople = ref<any[]>([])
  const selectedAccountIndex = ref(-1)
  const selectedAccounts = ref<any[]>([])
  
  const customerList = ref<any[]>([])
  const peopleList = ref<any[]>([])
  const accountList = ref<any[]>([])

  async function loadMasterData() {
    try {
      const [customers, people, accounts] = await Promise.all([
        loadCustomerOptions(),
        loadPeopleOptions(),
        loadAccountOptions()
      ])
      customerList.value = customers
      peopleList.value = people
      accountList.value = accounts
    } catch (error) {
      console.error('loadMasterData failed', error)
      ElMessage.warning('基础资料加载失败，请刷新重试')
    }
  }
  
  // 表单验证规则
  const rules = {
    customer: {
      required: true,
      message: '请选择客户',
      trigger: 'change',
    },
    time: {
      required: true,
      message: '请选择单据日期',
      trigger: 'change',
    },
    number: {
      required: true,
      message: '请输入单据编号',
      trigger: 'blur',
    },
  }
  
  // 计算属性
  const uploadAction = computed(() => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    return `${baseUrl}/imy/upload`
  })
  
  const hasEditPermission = computed(() => {
    return true
  })
  
  const hasExaminePermission = computed(() => {
    return true
  })
  
  // 状态信息
  const totalCount = computed(() => {
    return tableData.value.length
  })
  
  const totalAmount = computed(() => {
    const total = tableData.value.reduce((sum, row) => {
      const amount = parseFloat(row.money) || 0
      return sum + amount
    }, 0)
    return total.toFixed(2)
  })
  
  // 添加初始行
  const addInitialRows = () => {
    const initialRows = [
      {
        uniqid: generateUniqid(),
        accountId: null,
        account: "点击选择",
        money: "",
        settle: "",
        data: "",
      }
    ]
    tableData.value = [...initialRows]
    runHandleGrid()
  }
  
  const addGridRow = () => {
    const newRow = {
      uniqid: generateUniqid(),
      accountId: null,
      account: "点击选择",
      money: "",
      settle: "",
      data: "",
    }
    tableData.value = [...tableData.value, newRow]
    runHandleGrid()
  }
  
  const addRowAt = (index: number) => {
    const newRow = {
      uniqid: generateUniqid(),
      accountId: null,
      account: "点击选择",
      money: "",
      settle: "",
      data: "",
    }
    const newData = [...tableData.value]
    newData.splice(index + 1, 0, newRow)
    tableData.value = newData
    runHandleGrid()
  }

  const removeRow = (index: number) => {
    const newData = [...tableData.value]
    newData.splice(index, 1)
    tableData.value = newData
    runHandleGrid()
  }
  
  const runHandleGrid = () => {
    // 汇总信息
    summary()
  }
  
  const summary = () => {
    let total = 0
    tableData.value.forEach((item) => {
      total += parseFloat(item.money) || 0
    })
    form.total = total
  }
  
  // 处理金额输入
  const handleMoneyInput = (row: any) => {
    // 可以添加输入验证逻辑
    runHandleGrid()
  }
  
  // 格式化金额显示
  const formatMoney = (row: any) => {
    if (row.money) {
      const num = parseFloat(row.money)
      if (!isNaN(num)) {
        row.money = num.toFixed(2)
      } else {
        row.money = ""
      }
    }
    runHandleGrid()
  }
  
  // 初始化
  const init = () => {
    if (props.source == null) {
      form.time = new Date().toISOString().split('T')[0]
      form.number = 'SKD' + new Date().toISOString().replace(/[-:T.Z]/g, '').slice(2, 15)
      // 初始化表格数据
      addInitialRows()
    } else {
      loadExistingData()
    }
  }
  
  // 打开账户选择
  const openAccountSelection = (index: number) => {
    selectedAccountIndex.value = index
    accountSelectionVisible.value = true
    nextTick(() => {
      if (accountTableRef.value) {
        accountTableRef.value.clearSelection()
      }
    })
  }
  
  const handlePeopleSelect = (peopleId: string) => {
    const person = peopleList.value.find((item) => item.人员编号 === peopleId)
    form.people = peopleId || null
    form.peopleName = person?.人员名称 || ''
  }

  const handleAccountSelect = (row: any, accountId: string) => {
    const account = accountList.value.find((item) => item.账户编号 === accountId)
    row.accountId = accountId || null
    row.account = account?.账户名称 || ''
  }

  // 客户选择相关方法
  const openCustomerDialog = () => {
    customerDialogVisible.value = true
    nextTick(() => {
      if (customerTableRef.value) {
        customerTableRef.value.clearSelection()
      }
    })
  }
  
  const handleCustomerSelection = (selection: any[]) => {
    currentCustomer.value = selection
  }
  
  const confirmCustomer = () => {
    if (currentCustomer.value.length > 0) {
      const names = currentCustomer.value.map(item => item.客户名称).join(', ')
      form.customerName = names
      form.customer = currentCustomer.value.map(item => item.客户编号).join(',')
      customerDialogVisible.value = false
    } else {
      ElMessage.warning('请选择客户')
    }
  }
  
  // 人员选择相关方法
  const openPeopleDialog = () => {
    peopleDialogVisible.value = true
    nextTick(() => {
      if (peopleTableRef.value) {
        peopleTableRef.value.clearSelection()
      }
    })
  }
  
  const handlePeopleSelection = (selection: any[]) => {
    currentPeople.value = selection
  }
  
  const confirmPeople = () => {
    if (currentPeople.value.length > 0) {
      const names = currentPeople.value.map(item => item.人员名称).join(', ')
      form.peopleName = names
      form.people = currentPeople.value.map(item => item.人员编号).join(',')
      peopleDialogVisible.value = false
    } else {
      ElMessage.warning('请选择人员')
    }
  }
  
  // 账户选择相关方法
  const handleAccountSelection = (selection: any[]) => {
    selectedAccounts.value = selection
  }
  
  const confirmAccount = () => {
    if (selectedAccounts.value.length > 0 && selectedAccountIndex.value !== -1) {
      const account = selectedAccounts.value[0]
      const newData = [...tableData.value]
      newData[selectedAccountIndex.value].account = `${account.账户名称} (${account.账户编号})`
      newData[selectedAccountIndex.value].accountId = account.账户编号
      tableData.value = newData
      accountSelectionVisible.value = false
      selectedAccountIndex.value = -1
    } else {
      ElMessage.warning('请选择账户')
    }
  }
  
  // 格式化货币
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY'
    }).format(value)
  }
  
  // 保存单据
  const save = async () => {
    try {
      await formRef.value?.validate()
      const userStore = useUserStore()
      const body = {
        customer: form.customer,
        time: toDateTime(form.time),
        number: form.number,
        total: form.total,
        people: form.people,
        file: toFileField(uploadFiles.value, 'array'),
        data: form.data,
        user: userStore.getUser?.id || '',
        frame: '0',
        info: tableData.value.filter(row => row.accountId).map(item => ({
          account: item.accountId,
          amount: item.money,
          money: item.money,
          settle: item.settle,
          data: item.data,
        }))
      }

      if (form.id) {
        const res = await ReceiptAPI.update(String(form.id), body)
        if (res?.code !== 10000) throw new Error(res?.data || res?.message || '保存失败')
      } else {
        const res = await ReceiptAPI.add(body)
        if (res?.code !== 10000) throw new Error(res?.data || res?.message || '保存失败')
        if (res?.data) form.id = res.data as any
      }

      ElMessage.success('收款单保存成功')
      router.push({ path: '/receipt-order-report', query: { number: form.number } }).catch(() => {})
    } catch (error: unknown) {
      // http 拦截器已弹过错时不再重复提示
      if (error && typeof error === 'object' && 'data' in error) return
      ElMessage.error(error instanceof Error ? error.message : '保存失败')
    }
  }
  
  // 审核/反审核
  const examine = async () => {
    try {
      if (!form.id) {
        ElMessage.warning('请先保存单据再审核')
        return
      }
      const res = await ReceiptAPI.audit({ ids: [String(form.id)] })
      if (res?.code !== 10000) throw new Error(res?.message || '审核失败')
      form.examine = form.examine == 0 ? 1 : 0
      ElMessage.success((form.examine == 0 ? '反审核' : '审核') + '单据成功!')
    } catch (error: unknown) {
      ElMessage.error(error instanceof Error ? error.message : '审核失败')
    }
  }
  
  // 页面刷新
  const reload = async () => {
    await loadMasterData()
    init()
    ElMessage.success('页面刷新成功!')
  }
  
  function resolveCustomerDisplay(idOrName: string | null | undefined) {
    if (!idOrName) return { id: '', name: '' }
    const key = String(idOrName)
    const found = customerList.value.find(
      (c) => c.客户编号 === key || c.id === key || c.客户名称 === key
    )
    return { id: found ? (found.客户编号 || found.id) : key, name: found?.客户名称 || key }
  }

  function resolvePeopleDisplay(idOrName: string | null | undefined) {
    if (!idOrName) return { id: '', name: '' }
    const key = String(idOrName)
    const found = peopleList.value.find(
      (p) => p.人员编号 === key || p.id === key || p.人员名称 === key
    )
    return { id: found ? (found.人员编号 || found.id) : key, name: found?.人员名称 || key }
  }

  function resolveAccountDisplay(idOrName: string | null | undefined) {
    if (!idOrName) return { id: '', name: '' }
    const key = String(idOrName)
    const found = accountList.value.find(
      (a) => a.账户编号 === key || a.id === key || a.账户名称 === key
    )
    return { id: found ? (found.账户编号 || found.id) : key, name: found?.账户名称 || key }
  }

  // 加载已有数据
  const loadExistingData = async () => {
    try {
      if (!props.source) {
        runHandleGrid()
        return
      }
      const res = await ReceiptAPI.detail(String(props.source))
      if (res?.code === 10000 && res.data) {
        const d = res.data as Record<string, unknown>
        form.id = Number(d.id) || Number(props.source) || 0
        const customer = resolveCustomerDisplay(String(d.customer ?? ''))
        form.customer = customer.id || null
        form.customerName = customer.name
        form.time = d.time ? String(d.time).slice(0, 10) : form.time
        form.number = String(d.number ?? '')
        form.total = Number(d.total) || 0
        const people = resolvePeopleDisplay(String(d.people ?? ''))
        form.people = people.id || null
        form.peopleName = people.name
        form.data = String(d.data ?? '')
        form.examine = Number(d.examine) || 0
        const account = resolveAccountDisplay(String(d.account ?? ''))
        tableData.value = [{
          uniqid: generateUniqid(),
          accountId: account.id || d.account,
          account: account.name || String(d.account ?? ''),
          money: String(d.money ?? ''),
          settle: String(d.settle ?? ''),
          data: String(d.data ?? ''),
        }]
      }
      runHandleGrid()
    } catch (error: unknown) {
      ElMessage.error(error instanceof Error ? error.message : '加载失败')
    }
  }
  
  // 初始化
  onMounted(async () => {
    await loadMasterData()
    init()
  })
  </script>
  
  <style scoped>
  .imy.bill {
    height: 100%;
    padding: 16px;
    display: flex;
    flex-direction: column;
  }
  
  .search-select-container {
    display: flex;
    align-items: center;
  }
  
  .table-container {
    flex: 1;
    margin: 16px 0;
    border: 1px solid #ebeef5;
    border-radius: 4px;
    overflow: hidden;
    min-height: 300px;
  }
  
  .table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background-color: #f5f7fa;
    border-bottom: 1px solid #ebeef5;
  }
  
  .table-title {
    font-weight: bold;
    color: #303133;
  }
  
  .table-actions {
    display: flex;
    gap: 8px;
  }
  
  .settlement-table-container {
    padding: 0;
  }
  
  .table-footer {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    padding: 12px 16px;
    background-color: #f5f7fa;
    border-top: 1px solid #ebeef5;
    font-size: 14px;
    color: #606266;
  }
  
  .footer-info {
    display: flex;
    align-items: center;
  }
  
  .clickable-text {
    color: #409eff;
    cursor: pointer;
  }
  
  .clickable-text:hover {
    text-decoration: underline;
  }

  .th-gear { cursor: pointer; }
  
  .billExamine {
    height: 24px;
  }
  
  .layerBtn {
    margin-top: 16px;
    text-align: center;
  }
  
  .fistDivider {
    margin: 16px 0;
  }
  
  .dialog-content {
    max-height: 60vh;
    overflow: auto;
  }
  
  .add-row-btn, .del-row-btn {
    width: 24px;
    height: 24px;
    min-width: 24px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
  }
  
  /* 调整表格样式 */
  :deep(.settlement-table-container .el-table) {
    border: none;
  }
  
  :deep(.settlement-table-container .el-table th) {
    background-color: #f5f7fa;
    color: #606266;
    font-weight: 600;
  }
  
  :deep(.settlement-table-container .el-table .el-input__inner) {
    border: none;
    background: transparent;
  }
  
  :deep(.settlement-table-container .el-table .el-input__inner:focus) {
    background: #fff;
    border: 1px solid #409eff;
  }
  </style>