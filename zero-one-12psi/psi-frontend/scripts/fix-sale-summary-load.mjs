import fs from 'fs'

const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleSummary.vue'
let s = fs.readFileSync(file, 'utf8')

const replacement = `const mapBackendRowToItem = (item: any): SalesSummaryRow => {
  return {
    id: item.id ?? undefined,
    personName: item.personName ?? item.people ?? '',
    userName: item.userName ?? item.user ?? '',
    customerName: item.customerName ?? item.customer ?? '',
    productName: item.productName ?? item.goods ?? '',
    auxiliaryAttr: item.auxiliaryAttr ?? item.attr ?? '',
    warehouse: item.warehouse ?? '',
    unit: item.unit ?? '',
    billDate: item.billDate ?? item.date ?? '',
    saleUnitPrice: Number(item.sales?.price ?? 0),
    saleQuantity: Number(item.sales?.quantity ?? 0),
    saleAmount: Number(item.sales?.amount ?? 0),
    saleReturnUnitPrice: Number(item.returnSales?.price ?? 0),
    saleReturnQuantity: Number(item.returnSales?.quantity ?? 0),
    saleReturnAmount: Number(item.returnSales?.amount ?? 0),
    totalQuantity: Number(item.summary?.totalQuantity ?? 0),
    totalAmount: Number(item.summary?.totalAmount ?? 0)
  }
}

const loadTableData = async () => {
  loading.value = true
  try {
    const params: SalesSummaryUsingGetParams = {
      pageIndex: currentPage.value,
      pageSize: pageSize.value,
      ...buildCommonParams()
    } as SalesSummaryUsingGetParams

    const res = await salesSummaryUsingGet({ params })
    const anyRes: any = res
    let pageWrapper: any

    if (anyRes?.data?.data?.rows || anyRes?.data?.data?.total != null) {
      pageWrapper = anyRes.data.data
    } else if (anyRes?.data?.rows || anyRes?.data?.total != null) {
      pageWrapper = anyRes.data
    } else if (anyRes?.rows || anyRes?.total != null) {
      pageWrapper = anyRes
    } else {
      console.warn('【销售汇总】未识别的分页结构', anyRes)
    }

    const list = pageWrapper?.rows ?? []
    const totalCount = pageWrapper?.total ?? 0

    originalTableData.value = list.map((item: any) => mapBackendRowToItem(item))
    total.value = totalCount
  } catch (error: any) {
    console.error('获取销售汇总失败', error)
    ElMessage.error(error?.message || '获取销售汇总失败')
    originalTableData.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  const searchConditions: string[] = []
  if (searchForm.warehouse) searchConditions.push(\`仓库：\${searchForm.warehouse}\`)
  if (searchForm.goods) searchConditions.push(\`商品：\${searchForm.goods}\`)
  if (searchForm.customer) searchConditions.push(\`客户：\${searchForm.customer}\`)
  if (searchForm.user) searchConditions.push(\`用户：\${searchForm.user}\`)
  if (searchForm.people) searchConditions.push(\`人员：\${searchForm.people}\`)
  if (searchForm.startTime && searchForm.endTime) {
    searchConditions.push(\`日期：\${searchForm.startTime} ~ \${searchForm.endTime}\`)
  }

  const searchInfo =
    searchConditions.length > 0 ? \`搜索条件：\${searchConditions.join('，')}\` : '显示全部数据'

  searchPopoverVisible.value = false
  ElMessage.success(\`搜索完成，\${searchInfo}\`)
  currentPage.value = 1
  loadTableData()
}

`

s = s.replace(/\/\/ 加载表格数据[\s\S]*?\/\/ 重置搜索/, replacement + '// 重置搜索')
fs.writeFileSync(file, s, 'utf8')
console.log('SaleSummary loadTableData rebuilt')
