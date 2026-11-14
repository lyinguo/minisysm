import fs from 'fs'

const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleReceipt.vue'
let s = fs.readFileSync(file, 'utf8')

s = s.replace(
  /\/\/ 单据类型：[\s\S]*?params\.type = form\.orderType as string\n  \}/,
  `// 单据类型
  if (form.orderType) {
    params.type = form.orderType as string
  }`
)

const replacement = `const mapBackendRowToItem = (item: any, index: number): SalesReceiptRow => {
  const nucleus = item.nucleus as 0 | 1 | 2 | undefined
  let writeOffStatus = ''
  if (nucleus === 0) writeOffStatus = '未核销'
  else if (nucleus === 1) writeOffStatus = '部分核销'
  else if (nucleus === 2) writeOffStatus = '已核销'

  return {
    id: item.id ?? index,
    orderType: item.type ?? '',
    orgName: item.frame ?? '',
    customerName: item.customer ?? '',
    orderDate: item.time ?? '',
    orderNo: item.number ?? '',
    orderAmount: item.total ?? 0,
    actualAmount: item.actual ?? 0,
    receivedAmount: item.invoiceCollection ?? 0,
    receivableBalance: item.accountsReceivableBalance ?? 0,
    receiptRate: item.collectionRate ?? 0,
    writeOffStatus,
    remark: item.data ?? ''
  }
}

// ===================== 5. 调用查询接口，做字段映射 =====================
const fetchTableData = async () => {
  loading.value = true
  try {
    const params: SalesReceiptUsingGetParams = {
      pageIndex: currentPage.value,
      pageSize: pageSize.value,
      ...(buildSearchParams() as any)
    }

    const res = await salesReceiptUsingGet({ params })
    const anyRes: any = res

    let pageWrapper: PageDTO13 | undefined

    if (anyRes?.data?.data?.rows || anyRes?.data?.data?.total != null) {
      pageWrapper = anyRes.data.data as PageDTO13
    } else if (anyRes?.data?.rows || anyRes?.data?.total != null) {
      pageWrapper = anyRes.data as PageDTO13
    } else if (anyRes?.rows || anyRes?.total != null) {
      pageWrapper = anyRes as PageDTO13
    } else {
      console.warn('【销售收款表】未识别的分页结构', anyRes)
    }

    const rows = pageWrapper?.rows ?? []
    const totalCount = pageWrapper?.total ?? 0

    tableData.value = rows.map((item: any, index: number) => mapBackendRowToItem(item, index))
    total.value = totalCount
  } catch (error: any) {
    console.error('获取销售收款表失败', error)
    ElMessage.error(error?.message || '获取销售收款表失败')
    tableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}`

s = s.replace(
  /\/\/ ===================== 5\. 调用查询接口[\s\S]*?^}\n\n\/\/ ===================== 6\./m,
  replacement + '\n\n// ===================== 6.'
)

fs.writeFileSync(file, s, 'utf8')
console.log('SaleReceipt fixed')
