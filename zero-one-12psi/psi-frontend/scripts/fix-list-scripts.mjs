import fs from 'fs'

function fixListScript(filePath) {
  let s = fs.readFileSync(filePath, 'utf8')

  s = s.replace(/\/\/ 辅助属[^\n]*\n    auxiliaryAttr:/g, '    auxiliaryAttr:')
  s = s.replace(/\/\/ 折扣[^\n]*\n    discount:/g, '    discount:')
  s = s.replace(/\/\/ 总成[^\n]*\n    totalCost:/g, '    totalCost:')

  s = s.replace(
    /\/\/ 👉 决定导出范围[\s\S]*?pageIndex: 1, pageSize: 99999\n    const params:/g,
    '    const params:'
  )

  s = s.replace(/\nconst res = await/g, '\n    const res = await')
  s = s.replace(/\nconst blob: Blob/g, '\n    const blob: Blob')

  s = s.replace(
    /ElMessage\.info\('已重置搜索条件'\)\n  ElMessage\.success\('数据已刷新'\)/g,
    "ElMessage.info('已重置搜索条件')\n  currentPage.value = 1\n  fetchTableData()\n  ElMessage.success('数据已刷新')"
  )

  fs.writeFileSync(filePath, s, 'utf8')
  console.log('fixed script', filePath)
}

fixListScript('D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/purchase/PurchaseList.vue')
fixListScript('D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report/sales/SaleList.vue')
