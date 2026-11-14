import fs from 'fs'

const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleProfit.vue'
let s = fs.readFileSync(file, 'utf8')

const replacement = `// 刷新功能
const handleRefresh = () => {
  if (goodSearchRef.value) {
    goodSearchRef.value.resetForm()
  }
  Object.assign(searchFormData, {
    customer: null,
    number: '',
    startTime: '',
    endTime: '',
    user: null,
    people: null,
    orderType: '',
    showDetails: '隐藏明细'
  })
  showDetails.value = false
  loadData()
  ElMessage.success('已刷新数据')
}

const handleExport = async () => {
  try {
    const res = await salesProfitOpenApiExportUsingGet({ params: buildApiParams() })
    downloadExportBlob(res, \`销售利润表_\${new Date().toISOString().split('T')[0]}.xlsx\`)
    ElMessage.success('导出成功')
  } catch (error: unknown) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  }
}

`

s = s.replace(/\/\/ 刷新功能[\s\S]*?\/\/ 分页相关/, replacement + '// 分页相关')
fs.writeFileSync(file, s, 'utf8')
console.log('SaleProfit fixed')
