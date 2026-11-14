import fs from 'fs'

// Fix template labels
{
  let s = fs.readFileSync(
    'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/warehouse/InventoryReceiptDetail.vue',
    'utf8'
  )
  s = s.replace(/label="往来单[^\n"]*\n/g, 'label="往来单位"\n')
  fs.writeFileSync(
    'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/warehouse/InventoryReceiptDetail.vue',
    s,
    'utf8'
  )
}

// Fix InventoryReceiptDetail script block
{
  const file =
    'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/warehouse/InventoryReceiptDetail.vue'
  let s = fs.readFileSync(file, 'utf8')

  s = s.replace(
    /interface InOutBalance \{[\s\S]*?bct: number[^\n]*\n\ninterface TableRow/,
    `interface InOutBalance {
  uct: number
  uns: number
  bct: number
}

interface TableRow`
  )

  const replacement = `const exportFileName = ref('商品收发明细表')
const exportDataList = computed(() => {
  return tableData.value.map((row) => ({
    '单据类型': row.extension?.type || '',
    '所属组织': row.sourceData?.frameData?.name || '',
    '往来单位': row.current?.name || '',
    '单据时间': row.sourceData?.time || '',
    '单据编号': row.sourceData?.number || '',
    '商品名称': row.goodsData?.name || '',
    '辅助属性': row.attr || '',
    '仓库': row.warehouseData?.name || '',
    '单位': row.unit || '',
    '入库-成本': row.in?.uct || 0,
    '入库-数量': row.in?.uns || 0,
    '入库-总成本': row.in?.bct || 0,
    '出库-成本': row.out?.uct || 0,
    '出库-数量': row.out?.uns || 0,
    '出库-总成本': row.out?.bct || 0,
    '汇总-成本': row.balance?.uct || 0,
    '汇总-数量': row.balance?.uns || 0,
    '汇总-总成本': row.balance?.bct || 0
  }))
})

function buildDetailParams(): Record<string, unknown> {
  const params: Record<string, unknown> = {
    pageIndex: pagination.pageIndex,
    pageSize: pagination.pageSize
  }
  if (searchForm.value.goods) params.productName = searchForm.value.goods
  if (searchForm.value.warehouse) params.warehouseId = searchForm.value.warehouse
  if (searchForm.value.startTime) params.beginTime = searchForm.value.startTime
  if (searchForm.value.endTime) params.endTime = searchForm.value.endTime
  if (Array.isArray(searchForm.value.mold) && searchForm.value.mold.length) {
    params.mold = searchForm.value.mold
  }
  return params
}

async function loadData(page?: number) {
  if (page !== undefined) {
    pagination.pageIndex = page
  }

  loading.value = true

  try {
    const res = await WarehouseReportAPI.detailList(buildDetailParams())
    const { rows, total } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    tableData.value = rows as TableRow[]
    pagination.total = total
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    pagination.total = 0
    ElMessage.error(error instanceof Error ? error.message : '加载收发明细失败')
  } finally {
    loading.value = false
  }
}

`

  s = s.replace(
    /const exportFileName = ref\('商品收发明细表'\)[\s\S]*?\/\*\*\n \* 处理搜索\n \*\//,
    replacement + '/**\n * 处理搜索\n */'
  )

  fs.writeFileSync(file, s, 'utf8')
  console.log('InventoryReceiptDetail fixed')
}

// Fix InventoryReceiptSummary corrupted tail
{
  const file =
    'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/warehouse/InventoryReceiptSummary.vue'
  let s = fs.readFileSync(file, 'utf8')

  s = s.replace(
    /'汇总-成本': row\.balance\?\.uns \|\| 0,\s*'汇总-成本': unknown\) \{[\s\S]*?loading\.value = false\n  \}\n\}/,
    `'汇总-成本': row.balance?.uct || 0,
    '汇总-数量': row.balance?.uns || 0,
    '汇总-总成本': row.balance?.bct || 0
  }))
})

function buildSummaryParams(): Record<string, unknown> {
  const params: Record<string, unknown> = {
    pageIndex: pagination.pageIndex,
    pageSize: pagination.pageSize
  }
  if (searchForm.value.goods) params.productName = searchForm.value.goods
  if (searchForm.value.warehouse) params.warehouseId = searchForm.value.warehouse
  if (searchForm.value.startTime) params.beginTime = searchForm.value.startTime
  if (searchForm.value.endTime) params.endTime = searchForm.value.endTime
  return params
}

async function loadData(page?: number) {
  if (page !== undefined) {
    pagination.pageIndex = page
  }

  loading.value = true

  try {
    const res = await WarehouseReportAPI.summaryList(buildSummaryParams())
    const { rows, total } = unwrapPage(
      res as { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }
    )
    tableData.value = rows as TableRow[]
    pagination.total = total
  } catch (error: unknown) {
    console.error('加载数据失败:', error)
    tableData.value = []
    pagination.total = 0
    ElMessage.error(error instanceof Error ? error.message : '加载收发汇总失败')
  } finally {
    loading.value = false
  }
}`
  )

  fs.writeFileSync(file, s, 'utf8')
  console.log('InventoryReceiptSummary fixed')
}
