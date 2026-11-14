import fs from 'fs'

// Fix SaleList interface
{
  const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleList.vue'
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/)
  const start = lines.findIndex((l) => l.includes('interface SalesRankingRow'))
  const end = lines.findIndex((l, i) => i > start && l.startsWith('interface SearchForm'))
  const replacement = [
    'interface SalesRankingRow {',
    '  id?: number | string',
    '  productName: string',
    '  auxiliaryAttr: string',
    '  productCode: string',
    '  specification: string',
    '  unit: string',
    '  quantity: number',
    '  discount: number',
    '  tax: number',
    '  totalWithTax: number',
    '  cost: number',
    '  totalCost: number',
    '  grossProfit: number',
    '  grossProfitMargin: number',
    '}',
    ''
  ]
  lines.splice(start, end - start, ...replacement)
  fs.writeFileSync(file, lines.join('\n'), 'utf8')
  console.log('SaleList interface fixed')
}

// Fix SaleSummary filteredTableData
{
  const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleSummary.vue'
  let s = fs.readFileSync(file, 'utf8')
  s = s.replace(
    /\/\/ 当按商品[\s\S]*?return result\n\}\)/,
    `const filteredTableData = computed(() => {
  let result = [...originalTableData.value]
  const startTime = searchForm.startTime
  const endTime = searchForm.endTime

  if (startTime && endTime) {
    result = result.filter((item) => {
      if (!item.billDate) return false
      const billDate = new Date(item.billDate)
      const startDate = new Date(startTime)
      const endDateObj = new Date(endTime)
      return billDate >= startDate && billDate <= endDateObj
    })
  } else if (startTime) {
    result = result.filter((item) => {
      if (!item.billDate) return false
      const billDate = new Date(item.billDate)
      const startDate = new Date(startTime)
      return billDate >= startDate
    })
  } else if (endTime) {
    result = result.filter((item) => {
      if (!item.billDate) return false
      const billDate = new Date(item.billDate)
      const endDateObj = new Date(endTime)
      return billDate <= endDateObj
    })
  }

  return result
})`
  )

  s = s.replace(
    /\/\/  筛选类型改变处[^\n]*\nconst handleFilterTypeChange = \(\) => \{\n  \/\/ 重置相关字段[^\n]*\n  if \(searchForm\.filterType !== 'customer'\)/,
    `const handleFilterTypeChange = () => {
  if (searchForm.filterType !== 'customer')`
  )

  fs.writeFileSync(file, s, 'utf8')
  console.log('SaleSummary fixed')
}
