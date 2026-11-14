import fs from 'fs'
import path from 'path'

const reportDir = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report'

const replacements = [
  // exportFileName broken strings
  [/ref\('其他收支明细[^']*?\)/g, "ref('其他收支明细表')"],
  [/ref\('客户对账[^']*?\)/g, "ref('客户对账单')"],
  [/ref\('利润[^']*?\)/g, "ref('利润表')"],

  // ElMessage broken strings
  [/ElMessage\.warning\('请选择客户后搜[^']*?'\)/g, "ElMessage.warning('请选择客户后搜索')"],
  [/ElMessage\.warning\('请选择客户后导[^']*?'\)/g, "ElMessage.warning('请选择客户后导出')"],
  [/ElMessage\.success\('[^']*?'\)/g, (m) => {
    if (m.includes('ˢ') || m.includes('')) return "ElMessage.success('数据已刷新')"
    return m
  }],

  // export object keys
  [/'供应[^']*?:/g, "'供应商':"],
  [/\? '供应[^']*? :/g, "? '供应商' :"],

  // PayableDetail supplier key specifically
  [/'供应[^']*?: level/g, "'供应商': level"],

  // PurchasePayment merged interface - fix if present
  [/orgName: string \/\/所属组[^]*?supplierName: string \/\/供应[^]*?\n/g,
    'orgName: string // 所属组织\n  supplierName: string // 供应商\n'],
  [/payableBalance: number \/\/ 应付款余[^]*?paymentRate: number \/\/ 付款[^]*?writeOffStatus: string \/\/ 核销状[^]*?\n/g,
    'payableBalance: number // 应付款余额\n  paymentRate: number // 付款率\n  writeOffStatus: string // 核销状态\n'],
]

function walk(dir, files = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) walk(p, files)
    else if (e.name.endsWith('.vue')) files.push(p)
  }
  return files
}

let total = 0
for (const file of walk(reportDir)) {
  let s = fs.readFileSync(file, 'utf8')
  const orig = s
  for (const [re, rep] of replacements) {
    s = typeof rep === 'function' ? s.replace(re, rep) : s.replace(re, rep)
  }
  if (s !== orig) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed:', path.relative(reportDir, file))
    total++
  }
}
console.log('done', total)
