import fs from 'fs'

function fixPurchasePayment() {
  const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/purchase/PurchasePayment.vue'
  let s = fs.readFileSync(file, 'utf8')

  // remove duplicate broken handleExport comment block
  s = s.replace(
    /\n\/\/ 如果后面要改成直接调后端的导出接口[\s\S]*?\/\/ \}\n\nconst prepareExportData/,
    '\n\nconst prepareExportData'
  )

  // fix handleRefresh merged with formatCurrency
  s = s.replace(
    /const handleRefresh = \(\) => \{\s*handleResetSearch\(\)\s*currentPage\.value = 1\s*fetchTableData\(\)\s*ElMessage\.success\('数据已刷新'\) \|\| 0\s*return \(\s*'¥' \+\s*num\.toLocaleString\('zh-CN', \{[\s\S]*?\}\)\s*\)\s*\}/,
    `const formatCurrency = (value: number | string | null | undefined) => {
  const num = Number(value) || 0
  return (
    '¥' +
    num.toLocaleString('zh-CN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })
  )
}

const handleRefresh = () => {
  handleResetSearch()
  currentPage.value = 1
  fetchTableData()
  ElMessage.success('数据已刷新')
}`
  )

  // fix export object keys
  s = s.replace(/所属组. item\.orgName/g, '所属组织: item.orgName')
  s = s.replace(/供应. item\.supplierName/g, '供应商: item.supplierName')
  s = s.replace(/应付款余. item\.payableBalance/g, '应付款余额: item.payableBalance')
  s = s.replace(/付款. `\$\{item\.paymentRate\}%`/g, '付款率: `${item.paymentRate}%`')
  s = s.replace(/核销状. item\.writeOffStatus/g, '核销状态: item.writeOffStatus')

  fs.writeFileSync(file, s, 'utf8')
  console.log('PurchasePayment fixed')
}

function fixPurchaseDetail() {
  const file = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/purchase/PurchaseDetail.vue'
  let s = fs.readFileSync(file, 'utf8')

  s = s.replace(
    /\n\/\/  现在先用前端导出 CSV[\s\S]*?\/\/ \}\n\nconst prepareExportData/,
    '\n\nconst prepareExportData'
  )

  s = s.replace(/所属组. item\.orgName/g, '所属组织: item.orgName')
  s = s.replace(/供应. item\.supplierName/g, '供应商: item.supplierName')
  s = s.replace(/辅助属. item\.auxiliaryAttr/g, '辅助属性: item.auxiliaryAttr')
  s = s.replace(/折扣. item\.discountAmount/g, '折扣额: item.discountAmount')

  fs.writeFileSync(file, s, 'utf8')
  console.log('PurchaseDetail fixed')
}

fixPurchasePayment()
fixPurchaseDetail()
