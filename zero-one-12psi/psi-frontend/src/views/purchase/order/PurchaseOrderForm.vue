<template>
    <div class="purchase-order-form">
      <!-- 顶部操作栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <!-- 左上角搜索组件 -->
          <DocumentListSearch kind="purchase" @search="onGoodSearch" />
        </div>
        <div class="toolbar-right">
          <div class="btn-join">
            <!-- 批量操作按钮组：当有选中项时显示 -->
            <template v-if="selected.length > 0">
              <el-popover
                class="btnGroupPopover"
                placement="bottom"
                popper-class="blockPopover"
                trigger="click"
              >
                <template #reference>
                  <el-button type="info">操作</el-button>
                </template>
                <ul>
                  <li @click="onBatchExamine(0)">审核</li>
                  <li @click="onBatchExamine(1)">反审核</li>
                  <li @click="onBatchCheck(0)">核对</li>
                  <li @click="onBatchCheck(1)">反核对</li>
                </ul>
              </el-popover>
              <el-button @click="onBatchDelete" type="info">删除</el-button>
            </template>
            <OperationButtons
              :show-add="false"
              :show-batch="true"
              :show-refresh="false"
              :table-columns="columns"
              :export-simple-report-api="handleExportSimpleReport"
              :selected-order-ids="selectedOrderIds"
              export-file-name="简单报表导出"
              @batch="onBatch"
              @import-data="onImportData"
            />
            <el-button :loading="refreshing" type="primary" @click="onRefresh">刷新</el-button>
          </div>
        </div>
      </div>
  
      <el-alert v-if="queryError" type="error" :closable="false" show-icon><template #title>{{ queryError }}</template><el-button @click="loadPurchaseList">重新加载</el-button></el-alert>
      <!-- 表格 + 固定横向滚动条 + 状态栏 -->
      <div class="table-section">
        <!-- 表格滚动容器 -->
        <div ref="tableWrapper" class="table-wrapper">
          <el-table
            ref="tableRef"
            v-loading="refreshing"
            :data="pagedData"
            border
            style="width: 100%"
            :header-cell-style="{ background: '#fafafa' }"
            @selection-change="handleSelectionChange"
          >
            <!-- 左侧固定选择列 -->
            <el-table-column fixed="left" type="selection" width="48" align="center" />
  
            <!-- 所属组织 -->
            <el-table-column
              prop="org"
              label="所属组织"
              width="120"
              align="center"
              header-align="center"
            />
  
            <!-- 供应商 -->
            <el-table-column
              prop="supplier"
              label="供应商"
              width="120"
              align="center"
              header-align="center"
            />
  
            <!-- 单据时间（可排序） -->
            <el-table-column label="单据时间" width="130" align="center" header-align="center">
              <template #header>
                <div class="header-sortable">
                  <span class="col-title">单据时间</span>
                  <div class="sort-vertical">
                    <el-icon
                      :class="{ active: sortKey === 'billTime' && sortOrder === 'asc' }"
                      @click.stop="sortTable('billTime', 'asc')"
                      ><ArrowUp
                    /></el-icon>
                    <el-icon
                      :class="{ active: sortKey === 'billTime' && sortOrder === 'desc' }"
                      @click.stop="sortTable('billTime', 'desc')"
                      ><ArrowDown
                    /></el-icon>
                  </div>
                </div>
              </template>
              <template #default="{ row }">
                {{ row.billTime }}
              </template>
            </el-table-column>
  
            <!-- 单据编号（可排序） -->
            <el-table-column label="单据编号" width="200" align="center" header-align="center">
              <template #header>
                <div class="header-sortable">
                  <span class="col-title">单据编号</span>
                  <div class="sort-vertical">
                    <el-icon
                      :class="{ active: sortKey === 'billNo' && sortOrder === 'asc' }"
                      @click.stop="sortTable('billNo', 'asc')"
                      ><ArrowUp
                    /></el-icon>
                    <el-icon
                      :class="{ active: sortKey === 'billNo' && sortOrder === 'desc' }"
                      @click.stop="sortTable('billNo', 'desc')"
                      ><ArrowDown
                    /></el-icon>
                  </div>
                </div>
              </template>
              <template #default="{ row }">
                {{ row.billNo }}
              </template>
            </el-table-column>
  
            <!-- 单据金额（可排序） -->
            <el-table-column label="单据金额" width="130" align="center" header-align="center">
              <template #header>
                <div class="header-sortable">
                  <span class="col-title">单据金额</span>
                  <div class="sort-vertical">
                    <el-icon
                      :class="{ active: sortKey === 'billAmount' && sortOrder === 'asc' }"
                      @click.stop="sortTable('billAmount', 'asc')"
                      ><ArrowUp
                    /></el-icon>
                    <el-icon
                      :class="{ active: sortKey === 'billAmount' && sortOrder === 'desc' }"
                      @click.stop="sortTable('billAmount', 'desc')"
                      ><ArrowDown
                    /></el-icon>
                  </div>
                </div>
              </template>
              <template #default="{ row }">
                {{ formatNumber(row.billAmount) }}
              </template>
            </el-table-column>
  
            <!-- 实际金额（可排序） -->
            <el-table-column label="实际金额" width="130" align="center" header-align="center">
              <template #header>
                <div class="header-sortable">
                  <span class="col-title">实际金额</span>
                  <div class="sort-vertical">
                    <el-icon
                      :class="{ active: sortKey === 'realAmount' && sortOrder === 'asc' }"
                      @click.stop="sortTable('realAmount', 'asc')"
                      ><ArrowUp
                    /></el-icon>
                    <el-icon
                      :class="{ active: sortKey === 'realAmount' && sortOrder === 'desc' }"
                      @click.stop="sortTable('realAmount', 'desc')"
                      ><ArrowDown
                    /></el-icon>
                  </div>
                </div>
              </template>
              <template #default="{ row }">
                {{ formatNumber(row.realAmount) }}
              </template>
            </el-table-column>
  
            <!-- 单据付款（可排序） -->
            <el-table-column label="单据付款" width="130" align="center" header-align="center">
              <template #header>
                <div class="header-sortable">
                  <span class="col-title">单据付款</span>
                  <div class="sort-vertical">
                    <el-icon
                      :class="{ active: sortKey === 'paymentAmount' && sortOrder === 'asc' }"
                      @click.stop="sortTable('paymentAmount', 'asc')"
                      ><ArrowUp
                    /></el-icon>
                    <el-icon
                      :class="{ active: sortKey === 'paymentAmount' && sortOrder === 'desc' }"
                      @click.stop="sortTable('paymentAmount', 'desc')"
                      ><ArrowDown
                    /></el-icon>
                  </div>
                </div>
              </template>
              <template #default="{ row }">
                {{ formatNumber(row.paymentAmount) }}
              </template>
            </el-table-column>
  
            <!-- 核销金额（可排序） -->
            <el-table-column label="核销金额" width="130" align="center" header-align="center">
              <template #header>
                <div class="header-sortable">
                  <span class="col-title">核销金额</span>
                  <div class="sort-vertical">
                    <el-icon
                      :class="{ active: sortKey === 'writeoffAmount' && sortOrder === 'asc' }"
                      @click.stop="sortTable('writeoffAmount', 'asc')"
                      ><ArrowUp
                    /></el-icon>
                    <el-icon
                      :class="{ active: sortKey === 'writeoffAmount' && sortOrder === 'desc' }"
                      @click.stop="sortTable('writeoffAmount', 'desc')"
                      ><ArrowDown
                    /></el-icon>
                  </div>
                </div>
              </template>
              <template #default="{ row }">
                {{ formatNumber(row.writeoffAmount) }}
              </template>
            </el-table-column>
  
            <!-- 单据费用（可排序） -->
            <el-table-column label="单据费用" width="130" align="center" header-align="center">
              <template #header>
                <div class="header-sortable">
                  <span class="col-title">单据费用</span>
                  <div class="sort-vertical">
                    <el-icon
                      :class="{ active: sortKey === 'feeAmount' && sortOrder === 'asc' }"
                      @click.stop="sortTable('feeAmount', 'asc')"
                      ><ArrowUp
                    /></el-icon>
                    <el-icon
                      :class="{ active: sortKey === 'feeAmount' && sortOrder === 'desc' }"
                      @click.stop="sortTable('feeAmount', 'desc')"
                      ><ArrowDown
                    /></el-icon>
                  </div>
                </div>
              </template>
              <template #default="{ row }">
                {{ formatNumber(row.feeAmount) }}
              </template>
            </el-table-column>
  
            <!-- 关联人员 -->
            <el-table-column
              prop="relatedPerson"
              label="关联人员"
              width="130"
              align="center"
              header-align="center"
            />
  
            <!-- 审核状态（黑白文字） -->
            <el-table-column label="审核状态" width="100" align="center" header-align="center">
              <template #default="{ row }">
                <span>{{ row.auditStatus }}</span>
              </template>
            </el-table-column>
  
            <!-- 入库状态 -->
            <el-table-column label="库存流水" width="120" align="center" header-align="center">
              <template #default="{ row }">
                <span>{{ row.stockStatus }}</span>
              </template>
            </el-table-column>
  
            <!-- 核销状态：已核销 / 部分核销 时带小表格弹出 -->
            <el-table-column label="核销状态" width="120" align="center" header-align="center">
              <template #default="{ row }">
                <div class="status-with-trigger" v-if="row.writeoffStatus">
                  <span>{{ row.writeoffStatus }}</span>
                  <el-popover
                    v-if="row.writeoffStatus === '已核销' || row.writeoffStatus === '部分核销'"
                    placement="bottom"
                    trigger="click"
                    width="520"
                   @show="loadAssociated(row)">
                    <div class="inner-pop-table" v-loading="row.associatedLoading"><el-alert v-if="row.associatedError" type="error" :title="row.associatedError" :closable="false" />
                      <table>
                        <thead>
                          <tr>
                            <th>单据类型</th>
                            <th>单据时间</th>
                            <th>单据编号</th>
                            <th>核销金额</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(d, i) in row.writeoffDetails" :key="i">
                            <td>{{ d.billType }}</td>
                            <td>{{ d.billTime }}</td>
                            <td>{{ d.billNo }}</td>
                            <td class="num">{{ formatNumber(d.amount) }}</td>
                          </tr>
                          <tr v-if="!row.writeoffDetails || row.writeoffDetails.length === 0">
                            <td colspan="4" class="empty">暂无数据</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <template #reference>
                      <el-button link class="mini-trigger">
                        <el-icon><ArrowDown /></el-icon>
                      </el-button>
                    </template>
                  </el-popover>
                </div>
              </template>
            </el-table-column>
  
            <!-- 费用状态：未结算 时可展开 -->
            <el-table-column label="费用状态" width="120" align="center" header-align="center">
              <template #default="{ row }">
                <div class="status-with-trigger" v-if="row.feeStatus">
                  <span>{{ row.feeStatus }}</span>
                  <el-popover
                    v-if="row.feeStatus !== '无需结算'"
                    placement="bottom"
                    trigger="click"
                    width="520"
                   @show="loadAssociated(row)">
                    <div class="inner-pop-table" v-loading="row.associatedLoading"><el-alert v-if="row.associatedError" type="error" :title="row.associatedError" :closable="false" />
                      <table>
                        <thead>
                          <tr>
                            <th>支出类别</th>
                            <th>金额</th>
                            <th>结算金额</th>
                            <th>结算状态</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(d, i) in row.feeDetails" :key="i">
                            <td>{{ d.expenseType }}</td>
                            <td class="num">{{ formatNumber(d.amount) }}</td>
                            <td class="num">{{ formatNumber(d.settleAmount) }}</td>
                            <td>{{ d.settleStatus }}</td>
                          </tr>
                          <tr v-if="!row.feeDetails || row.feeDetails.length === 0">
                            <td colspan="4" class="empty">暂无数据</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <template #reference>
                      <el-button link class="mini-trigger">
                        <el-icon><ArrowDown /></el-icon>
                      </el-button>
                    </template>
                  </el-popover>
                </div>
              </template>
            </el-table-column>
  
            <!-- 发票状态：已开具 时可展开 -->
            <el-table-column label="发票状态" width="120" align="center" header-align="center">
              <template #default="{ row }">
                <div class="status-with-trigger" v-if="row.invoiceStatus">
                  <span>{{ row.invoiceStatus }}</span>
                  <el-popover
                    v-if="['部分开票', '已开票'].includes(row.invoiceStatus)"
                    placement="bottom"
                    trigger="click"
                    width="520"
                   @show="loadAssociated(row)">
                    <div class="inner-pop-table" v-loading="row.associatedLoading"><el-alert v-if="row.associatedError" type="error" :title="row.associatedError" :closable="false" />
                      <table>
                        <thead>
                          <tr>
                            <th>开票日期</th>
                            <th>发票号码</th>
                            <th>发票抬头</th>
                            <th>发票金额</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(d, i) in row.invoiceDetails" :key="i">
                            <td>{{ d.invoiceDate }}</td>
                            <td>{{ d.invoiceNo }}</td>
                            <td>{{ d.invoiceTitle }}</td>
                            <td class="num">{{ formatNumber(d.invoiceAmount) }}</td>
                          </tr>
                          <tr v-if="!row.invoiceDetails || row.invoiceDetails.length === 0">
                            <td colspan="4" class="empty">暂无数据</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <template #reference>
                      <el-button link class="mini-trigger">
                        <el-icon><ArrowDown /></el-icon>
                      </el-button>
                    </template>
                  </el-popover>
                </div>
              </template>
            </el-table-column>
  
            <!-- 核对状态（普通文字） -->
            <el-table-column
              prop="checkStatus"
              label="核对状态"
              width="100"
              align="center"
              header-align="center"
            />
  
            <!-- 到货日期 -->
  
            <!-- 制单人 -->
            <el-table-column
              prop="maker"
              label="制单人"
              width="100"
              align="center"
              header-align="center"
            />
  
            <!-- 备注信息 -->
            <el-table-column
              prop="remark"
              label="备注信息"
              width="160"
              align="center"
              header-align="center"
              :show-overflow-tooltip="true"
            />
  
            <!-- 操作列 -->
            <el-table-column fixed="right" label="相关操作" width="170" align="center">
              <template #default="scope">
                <div class="op-row">
                  <el-button size="small" class="op-btn op-gray" @click="openDetail(scope.row)">
                    详情
                  </el-button>
                  <el-button size="small" class="op-btn op-gray" @click="onDelete(scope.row)">
                    删除
                  </el-button>
                  <el-dropdown trigger="click">
                    <el-button size="small" class="op-btn op-gray op-more">
                      <el-icon><ArrowDown /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu class="info-dropdown">
                        <el-dropdown-item>单据号：{{ scope.row.billNo }}</el-dropdown-item>
                        <el-dropdown-item>供应商：{{ scope.row.supplier }}</el-dropdown-item>
                        <el-dropdown-item
                          >金额：{{ formatNumber(scope.row.billAmount) }}</el-dropdown-item
                        >
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
  
        <!-- 中：我们的自定义横向拖动条 -->
        <div ref="xScroll" class="x-scroll">
          <div ref="xInner" class="x-scroll-inner"></div>
        </div>
  
        <!-- 底部状态栏 -->
        <div class="status-bar">
          <div class="status-left">
            <el-pagination
              background
              layout="prev, pager, next, sizes, jumper, total"
              :total="serverTotal"
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 30, 50, 100]"
            />
          </div>
          <div class="status-right">
            <span>本页单据金额：{{ totalBillAmount.toLocaleString(undefined, { maximumFractionDigits: 4 }) }}</span>
            <span class="ml-24">本页实际金额：{{ totalRealAmount.toLocaleString(undefined, { maximumFractionDigits: 4 }) }}</span>
            <span class="ml-24">本页单据付款：{{ totalPayment.toLocaleString(undefined, { maximumFractionDigits: 4 }) }}</span>
            <span class="ml-24">本页核销金额：{{ totalWriteoff.toLocaleString(undefined, { maximumFractionDigits: 4 }) }}</span>
            <span class="ml-24">本页单据费用：{{ totalFee.toLocaleString(undefined, { maximumFractionDigits: 4 }) }}</span>
          </div>
        </div>
      </div>
  
      <!-- 采购单详情弹窗 -->
      <PurchaseOrderDetailDialog
        v-model:visible="detailVisible"
        :record="currentRow"
        @save="handleDetailSave"
        @changed="loadPurchaseList"
      />
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick, type Ref } from 'vue'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
  import PurchaseOrderDetailDialog from './PurchaseOrderDetailDialog.vue'
  
  import DocumentListSearch from '@/components/trade/DocumentListSearch.vue'
  import { extractErrorMessage } from '@/apis/utils/jsonResponse'
  import OperationButtons from '@/components/operationbuttons/OperationButtons.vue'
  import { PurchaseNoteAPI } from '@/apis/purchase/purchaseOrder'
  
  /** 表格行结构 */
  interface WriteoffDetail {
    billType: string
    billTime: string
    billNo: string
    amount: number
  }
  
  interface FeeDetail {
    expenseType: string
    amount: number
    settleAmount: number
    settleStatus: string
  }
  
  interface InvoiceDetail {
    invoiceDate: string
    invoiceNo: string
    invoiceTitle: string
    invoiceAmount: number
  }
  
  interface RowData {
    id?: number | string // 订单ID
    org: string
    supplier: string
    billTime: string
    billNo: string
    billAmount: number
    realAmount: number
    paymentAmount: number
    writeoffAmount: number
    feeAmount: number
    relatedPerson: string
    auditStatus: string
    stockStatus: string
    writeoffStatus: string
    feeStatus: string
    invoiceStatus: string
    checkStatus: string
    arrivalDate: string
    maker: string
    remark: string
    associatedLoading?: boolean
    associatedLoaded?: boolean
    associatedError?: string
    writeoffDetails?: WriteoffDetail[]
    feeDetails?: FeeDetail[]
    invoiceDetails?: InvoiceDetail[]
  }
  
  const tableData = ref<RowData[]>([])
  const serverTotal = ref(0)
  const queryError = ref('')
  const appliedQuery = ref<Record<string, any>>({})
  let querySequence = 0
  async function loadPurchaseList() {
    const sequence = ++querySequence
    refreshing.value = true
    queryError.value = ''
    try {
      const response = await PurchaseNoteAPI.getList({ ...appliedQuery.value, pageIndex: currentPage.value, pageSize: pageSize.value })
      if (sequence !== querySequence) return
      if (response.code !== 10000 || !response.data) throw new Error(response.message || '采购单加载失败')
      serverTotal.value = Number(response.data.total || 0)
      const lastPage = Math.max(1, Math.ceil(serverTotal.value / pageSize.value))
      if (currentPage.value > lastPage) { currentPage.value = lastPage; return }
      selected.value = []
      tableRef.value?.clearSelection?.()
      tableData.value = (response.data.rows || []).map(item => ({
        id: item.id, org: item.frameName || item.frame, supplier: item.supplierName || item.supplier,
        billTime: String(item.time || '').replace('T', ' '), billNo: item.number,
        billAmount: Number(item.total || 0), realAmount: Number(item.actual || 0), paymentAmount: Number(item.buyMoney || 0),
        writeoffAmount: Number(item.billMoney || 0), feeAmount: Number(item.cost || 0), relatedPerson: item.peopleName || item.people || '',
        auditStatus: Number(item.examine) === 1 ? '已审核' : '未审核', stockStatus: `${Number(item.stockRecords || 0)} 条`,
        writeoffStatus: ['未核销', '部分核销', '已核销'][Number(item.nucleus)] || '未核销',
        feeStatus: ['未结算', '部分结算', '已结算', '无需结算'][Number(item.cse)] || '未结算',
        invoiceStatus: ['未开票', '部分开票', '已开票', '无需开具'][Number(item.invoice)] || '未开票',
        checkStatus: Number(item.checkStatus) === 1 ? '已核对' : '未核对', arrivalDate: '',
        maker: item.userName || item.noteUser || '', remark: item.data || '', writeoffDetails: [], feeDetails: [], invoiceDetails: []
      }))
      originalAllData.value = JSON.parse(JSON.stringify(tableData.value))
    } catch (error) {
      if (sequence !== querySequence) return
      tableData.value = []; serverTotal.value = 0
      queryError.value = extractErrorMessage(error)
    } finally { if (sequence === querySequence) refreshing.value = false }
  }

  // 给 OperationButtons 用的列描述（不是表格必须按这个渲染）
  const columns: Array<{ prop: string; label: string; width: number }> = [
    { prop: 'org', label: '所属组织', width: 120 },
    { prop: 'supplier', label: '供应商', width: 120 },
    { prop: 'billTime', label: '单据时间', width: 130 },
    { prop: 'billNo', label: '单据编号', width: 200 },
    { prop: 'billAmount', label: '单据金额', width: 130 },
    { prop: 'realAmount', label: '实际金额', width: 130 },
    { prop: 'paymentAmount', label: '单据付款', width: 130 },
    { prop: 'writeoffAmount', label: '核销金额', width: 130 },
    { prop: 'feeAmount', label: '单据费用', width: 130 },
    { prop: 'relatedPerson', label: '关联人员', width: 130 },
    { prop: 'auditStatus', label: '审核状态', width: 100 },
    { prop: 'stockStatus', label: '库存流水', width: 120 },
    { prop: 'writeoffStatus', label: '核销状态', width: 120 },
    { prop: 'feeStatus', label: '费用状态', width: 120 },
    { prop: 'invoiceStatus', label: '发票状态', width: 120 },
    { prop: 'checkStatus', label: '核对状态', width: 100 },
    { prop: 'maker', label: '制单人', width: 100 },
    { prop: 'remark', label: '备注信息', width: 160 }
  ]

  /* 搜索部分 */
  type SearchFormData = {
    supplier?: string | null
    number?: string
    startTime?: string
    endTime?: string
    [k: string]: any
  }
  const searchModel = reactive<SearchFormData>({})


  const originalAllData = ref<RowData[]>([])

  /* 选择 */
  const selected = ref<RowData[]>([])
  const handleSelectionChange = (rows: RowData[]) => {
    selected.value = rows
  }
  
  // 获取选中的订单ID数组
  const selectedOrderIds = computed(() => {
    return selected.value.map(row => {
      // 优先使用 id 字段，如果没有则使用 billNo（单据编号）
      return (row as any).id || row.billNo || ''
    }).filter(id => id !== '')
  })
  
  // 导出简单报表的处理函数
  const handleExportSimpleReport = async (orderId: string | number) => {
    try {
      const result = await PurchaseNoteAPI.exportSimpleReport(orderId)
      return result
    } catch (error: any) {
      console.error('导出简单报表失败:', error)
      throw error
    }
  }

  /* 排序 */
  const sortKey = ref<string>('')
  const sortOrder = ref<'asc' | 'desc' | ''>('')
  const sortTable = (key: string, order: 'asc' | 'desc') => {
    sortKey.value = key
    sortOrder.value = order
    tableData.value.sort((a, b) => {
      const va = (a as any)[key]
      const vb = (b as any)[key]
      if (order === 'asc') return va > vb ? 1 : va < vb ? -1 : 0
      return va < vb ? 1 : va > vb ? -1 : 0
    })
  }

  /* 合计 / 分页 */
  const totalBillAmount = computed(() => tableData.value.reduce((s, r) => s + (r.billAmount || 0), 0))
  const totalRealAmount = computed(() => tableData.value.reduce((s, r) => s + (r.realAmount || 0), 0))
  const totalPayment = computed(() => tableData.value.reduce((s, r) => s + (r.paymentAmount || 0), 0))
  const totalWriteoff = computed(() =>
    tableData.value.reduce((s, r) => s + (r.writeoffAmount || 0), 0)
  )
  const totalFee = computed(() => tableData.value.reduce((s, r) => s + (r.feeAmount || 0), 0))

  const currentPage = ref(1)
  const pageSize = ref(10)
  const pagedData = computed(() => tableData.value)
  const refreshing = ref(false)
  const onGoodSearch = (payload: Record<string, any>) => {
    appliedQuery.value = {
      number: payload.number?.trim() || undefined, supplier: payload.supplier?.trim() || undefined,
      name: payload.goods?.trim() || undefined, people: payload.people?.trim() || undefined,
      noteUser: payload.user?.trim() || undefined, data: payload.data?.trim() || undefined,
      examine: payload.examine, startTime: payload.startTime || undefined, endTime: payload.endTime || undefined
    }
    if (currentPage.value !== 1) currentPage.value = 1
    else void loadPurchaseList()
  }
  const onRefresh = () => { if (!refreshing.value) void loadPurchaseList() }
  watch(currentPage, () => { void loadPurchaseList() })
  watch(pageSize, () => { if (currentPage.value !== 1) currentPage.value = 1; else void loadPurchaseList() })

  /* 批量 */
  const onBatch = () => {
    ElMessage.info('请先勾选需要操作的真实单据')
  }

  /* 导入（保持原逻辑） */
  const onImportData = (_rows: any[]) => {
    ElMessage.warning('采购导入尚未完成真实保存验收，本次数据没有写入系统')
  }

  async function loadAssociated(row: RowData) {
    if (row.associatedLoading || row.associatedLoaded || !row.id) return
    row.associatedLoading = true; row.associatedError = ''
    try {
      const response = await PurchaseNoteAPI.getDocument(String(row.id))
      if (response.code !== 10000 || !response.data) throw new Error(response.message || '关联记录读取失败')
      row.writeoffDetails = (response.data.settlements || []).map(item => ({ billType: ({ buy: '本单付款', omy: '付款单', bre: '采购退货单', bill: '核销单' } as Record<string, string>)[item.type] || item.type, billTime: String(item.time || '').replace('T', ' '), billNo: item.sourceNumber || item.source, amount: Number(item.money || 0) }))
      row.feeDetails = (response.data.expenses || []).map(item => ({ expenseType: item.expenseName || item.iet, amount: Number(item.money || 0), settleAmount: Number(item.settle || 0), settleStatus: ['未结算', '部分结算', '已结算'][Number(item.state || 0)] || '未结算' }))
      row.invoiceDetails = (response.data.invoices || []).map(item => ({ invoiceDate: String(item.time || '').replace('T', ' '), invoiceNo: item.number, invoiceTitle: item.title, invoiceAmount: Number(item.money || 0) }))
      row.associatedLoaded = true
    } catch (error) { row.associatedError = extractErrorMessage(error) }
    finally { row.associatedLoading = false }
  }

  /* 详情 */
  const detailVisible = ref(false)
  const currentRow = ref<RowData | null>(null)
  const openDetail = (row: RowData) => {
    currentRow.value = row
    detailVisible.value = true
  }
  const handleDetailSave = () => {
    detailVisible.value = false
    void loadPurchaseList()
  }
  // These old actions only changed memory. Their business implementations remain pending.
  const onDelete = (_row: RowData) => ElMessage.warning('采购删除引用保护尚在验收，本次未删除单据')
  const onBatchDelete = () => ElMessage.warning('采购批量删除尚在验收，本次未删除单据')
  const onBatchExamine = (_type: 0 | 1) => ElMessage.warning('采购审核库存和资金联动尚在修复，本次未修改审核状态')
  const onBatchCheck = (_type: 0 | 1) => ElMessage.warning('采购批量核对尚在验收，本次未修改单据状态')

  /* 固定横向滚动条联动 */
  const tableRef = ref()
  const tableWrapper = ref<HTMLElement | null>(null)
  const bodyWrapper = ref<HTMLElement | null>(null)
  const headerWrapper = ref<HTMLElement | null>(null)
  const xScroll = ref<HTMLElement | null>(null)
  const xInner = ref<HTMLElement | null>(null)
  let ro: ResizeObserver | null = null

  const setWidths = () => {
    if (!bodyWrapper.value || !xInner.value) return
    xInner.value.style.width = bodyWrapper.value.scrollWidth + 'px'
  }
  const bodyScroll = () => {
    if (!xScroll.value || !bodyWrapper.value) return
    if (xScroll.value.scrollLeft !== bodyWrapper.value.scrollLeft) {
      xScroll.value.scrollLeft = bodyWrapper.value.scrollLeft
    }
    if (headerWrapper.value) headerWrapper.value.scrollLeft = bodyWrapper.value.scrollLeft
  }
  const xScrollScroll = () => {
    if (!xScroll.value || !bodyWrapper.value) return
    if (bodyWrapper.value.scrollLeft !== xScroll.value.scrollLeft) {
      bodyWrapper.value.scrollLeft = xScroll.value.scrollLeft
      if (headerWrapper.value) headerWrapper.value.scrollLeft = xScroll.value.scrollLeft
    }
  }

  onMounted(async () => {
    void loadPurchaseList()

    await nextTick()
    const tableEl = (tableRef.value?.$el ?? null) as HTMLElement | null
    bodyWrapper.value = tableEl?.querySelector('.el-table__body-wrapper') as HTMLElement | null
    headerWrapper.value = tableEl?.querySelector('.el-table__header-wrapper') as HTMLElement | null

    if (bodyWrapper.value) {
      bodyWrapper.value.addEventListener('scroll', bodyScroll, { passive: true })
    }
    if (xScroll.value) {
      xScroll.value.addEventListener('scroll', xScrollScroll, { passive: true })
    }
    setWidths()
    if (bodyWrapper.value) {
      ro = new ResizeObserver(() => setWidths())
      ro.observe(bodyWrapper.value)
    }
  })

  onBeforeUnmount(() => {
    if (bodyWrapper.value) bodyWrapper.value.removeEventListener('scroll', bodyScroll)
    if (xScroll.value) xScroll.value.removeEventListener('scroll', xScrollScroll)
    if (ro && bodyWrapper.value) ro.unobserve(bodyWrapper.value)
    ro = null
  })

  /* 工具函数：数字加千分位 */
  const formatNumber = (n: number | undefined | null) => {
    const num = Number(n ?? 0)
    return Number.isFinite(num) ? num.toLocaleString(undefined, { maximumFractionDigits: 4 }) : '0'
  }
</script>

<style scoped>
.purchase-order-form {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #fff;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
}
.table-section {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  position: relative;
}
.table-wrapper { flex:1; min-height:0; min-width:0; width:100%; overflow:hidden; }
.x-scroll { display:none; }
/* 状态栏 */
.status-bar {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f7f8fa;
  border-top: 1px solid #ebeef5;
  min-height: 36px;
  flex-wrap: wrap;
  gap: 8px;
  padding: 4px 10px;
  font-size: 13px;
  color: #606266;
}
/* 左边分页不挤 */
.status-left {
  flex: 0 0 auto;
}
/* 右边合计不换行 */
.status-right {
  flex: 0 0 auto;
  white-space: normal;
  font-size: 13px;
  color: #606266;
}
.ml-24 {
  margin-left: 24px;
}

/* 顶部按钮联动 */
.btn-join {
  display: inline-flex;
  align-items: center;
}
.btn-join > * + * {
  margin-left: -1px;
}

/* 表头排序样式 */
.header-sortable {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.col-title {
  white-space: normal;
}
.sort-vertical {
  display: inline-flex;
  flex-direction: column;
  margin-left: 4px;
  line-height: 10px;
}
.sort-vertical .el-icon {
  font-size: 14px;
  color: #c0c4cc;
  cursor: pointer;
}
.sort-vertical .el-icon.active {
  color: #409eff;
}

/* 操作列按钮 */
.op-row {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.op-btn {
  min-height: 36px;
  flex-wrap: wrap;
  gap: 8px;
  line-height: 26px;
  background: #fff;
  color: #606266;
  border: 1px solid #dcdfe6;
  border-radius: 0;
  padding: 0 10px;
  transition: all 0.15s ease;
}
.op-row > * + * {
  margin-left: -1px;
}
.op-row :deep(.el-dropdown .el-button) {
  border-radius: 0 !important;
}
.op-row .op-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

/* 状态 + 小按钮 */
.status-with-trigger {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.mini-trigger {
  padding: 0;
  min-height: 20px;
}

/* 内部弹窗表格 */
.inner-pop-table {
  width: 100%;
}
.inner-pop-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.inner-pop-table th,
.inner-pop-table td {
  border: 1px solid #ebeef5;
  padding: 4px 6px;
  text-align: center;
  white-space: normal;
}
.inner-pop-table th {
  background: #f5f7fa;
  font-weight: 500;
}
.inner-pop-table td.num {
  text-align: right;
}
.inner-pop-table td.empty {
  text-align: center;
  color: #909399;
}

.mr-8 {
  margin-right: 8px;
}
</style>
<style scoped>
.purchase-order-form,.table-section{min-width:0;max-width:100%}.toolbar{flex-wrap:wrap;gap:12px}.toolbar-left{width:100%;min-width:0}.status-right{display:flex;flex-wrap:wrap;gap:8px}.status-right .ml-24{margin-left:0}
</style>

<style scoped>
.toolbar-right,.btn-join{max-width:100%;flex-wrap:wrap;gap:4px}.btn-join>*+*{margin-left:0}.status-left{max-width:100%;overflow-x:auto}
</style>
