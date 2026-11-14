import fs from 'fs'
import path from 'path'

const reportDir = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report'

function walk(dir) {
  const files = []
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name)
    if (fs.statSync(full).isDirectory()) files.push(...walk(full))
    else if (name.endsWith('.vue')) files.push(full)
  }
  return files
}

function repair(content, filePath) {
  let s = content

  // template label attributes broken by encoding
  s = s.replace(/label="汇.\s*align="/g, 'label="汇总" align="')
  s = s.replace(/label="采购.\s*align="/g, 'label="采购单" align="')

  // broken Chinese string literals (single corrupted char before closing quote)
  s = s.replace(/'采购.\)/g, "'采购单')")
  s = s.replace(/'采购.,/g, "'采购单',")
  s = s.replace(/=== '采购.\)/g, "=== '采购单')")
  s = s.replace(/: '采购.,/g, ": '采购单',")
  s = s.replace(/失.\)/g, "失败')")
  s = s.replace(/失.\?/g, "失败'")

  // merged ref declarations on one line
  s = s.replace(/(\]\)\(\[\]\)) \/\/ [^\n]*?(const \w+ = ref)/g, '$1\n$2')

  // merged comment + code on same line (common corruption)
  s = s.replace(/\/\/ [^\n]*?  if \(searchFormData\.orderType\)/g, (m) => {
    if (m.includes('orderType')) return '\n  if (searchFormData.orderType)'
    return m
  })
  s = s.replace(/\/\/ 0 = 采购退货单, 1 = 采购.  if \(searchFormData\.orderType\)/g, '\n  if (searchFormData.orderType)')

  // handleRefresh merged into handleExport
  s = s.replace(
    /ElMessage\.success\('数据已刷新'\) => \{/g,
    "ElMessage.success('数据已刷新')\n}\n\nconst handleExport = async () => {"
  )

  // fix broken startTime/endTime block in buildSearchParams
  s = s.replace(
    /\/\/ startTime: '', \/\/ 开始日期\s*\n\s*endTime: '' \/\/ 结束日期 -> endTime\s*\n\s*if \(searchFormData\.endTime\)/g,
    `if (searchFormData.startTime) {
    params.startTime = searchFormData.startTime as string
  }

  if (searchFormData.endTime)`
  )

  // fix merged field comments in object literals
  s = s.replace(/\/\/ 供应.        supplierName:/g, '// 供应商\n        supplierName:')
  s = s.replace(/\/\/TODO[^\n]*        unitType:/g, "// TODO 后端字段占位\n        unitType:")
  s = s.replace(/\/\/ 辅助属.        auxiliaryAttr:/g, '// 辅助属性\n        auxiliaryAttr:')
  s = s.replace(/\/\/ 折扣.        discountAmount:/g, '// 折扣额\n        discountAmount:')

  // fix export object keys missing quotes
  s = s.replace(/所属组. item\.orgName/g, '所属组织: item.orgName')
  s = s.replace(/供应. item\.supplierName/g, '供应商: item.supplierName')
  s = s.replace(/辅助属. item\.auxiliaryAttr/g, '辅助属性: item.auxiliaryAttr')
  s = s.replace(/折扣. item\.discountAmount/g, '折扣额: item.discountAmount')

  // fix broken console.log lines (remove garbage middle)
  s = s.replace(
    /console\.log\('【采购明细接口返回', total \}/g,
    "console.log('【采购明细接口返回】', res)\n    const anyRes: any = res\n    let pageWrapper: PageDTO9 | undefined\n    if (anyRes?.data?.rows) {\n      pageWrapper = anyRes.data as PageDTO9\n    } else if (anyRes?.rows) {\n      pageWrapper = anyRes as PageDTO9"
  )

  // fix parse log merged line
  s = s.replace(
    /\/\/ 再打印一下，方便你看 list 里是不是有东.    console\.log\('【解析后. rows., list/g,
    "console.log('【解析后 rows】', list"
  )

  // fix export blob missing assignment
  if (filePath.includes('PurchaseDetail')) {
    s = s.replace(
      /console\.log\('【采购明细表导出接口返回', \{\s*type: 'application\/vnd\.openxmlformats-officedocument\.spreadsheetml\.sheet'\s*\}\)/,
      `const anyRes: any = res
    const blob: Blob = anyRes?.data ?? anyRes`
    )
  }

  // PurchaseList broken params block
  s = s.replace(
    /\/\/ 👉 决定导出范围.\n    \/\/ - 当前页：pageIndex: currentPage\.value, pageSize: pageSize\.value\n    \/\/ - 当前条件下全部数据\n      pageIndex: 1, pageSize: 99999\n    const params:/g,
    `const params:`
  )

  // fix handleResetSearch missing close before handleExport injection
  if (s.includes("ElMessage.info('已重置搜索条件')") && !s.includes('const handleRefresh')) {
    s = s.replace(
      /(const handleResetSearch = \(\) => \{[\s\S]*?ElMessage\.info\('已重置搜索条件'\))\n\}/,
      `$1\n  currentPage.value = 1\n  fetchTableData()\n}\n\nconst handleRefresh = () => {\n  currentPage.value = 1\n  fetchTableData()\n`
    )
  }

  return s
}

for (const file of walk(reportDir)) {
  const original = fs.readFileSync(file, 'utf8')
  const fixed = repair(original, file)
  if (fixed !== original) {
    fs.writeFileSync(file, fixed, 'utf8')
    console.log('fixed:', path.basename(file))
  }
}

console.log('batch repair done')
