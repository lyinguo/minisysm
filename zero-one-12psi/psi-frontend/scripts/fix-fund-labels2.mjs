import fs from 'fs'
import path from 'path'

const reportDir = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report'

const fileFixes = {
  'fund/PayableDetail.vue': [
    [/label: '全部供应[^']*?, value: 0/g, "label: '全部供应商', value: 0"],
    [/label: '欠款供应[^']*?, value: 1/g, "label: '欠款供应商', value: 1"],
  ],
  'fund/DebtAgeAnalysis.vue': [
    [/label: '请输入单位名[^']*?\n/g, "label: '请输入单位名称'\n"],
    [/label: '请输入单位编[^']*?\n/g, "label: '请输入单位编号'\n"],
    [/label: '供应[^']*?, value: 'supplier'/g, "label: '供应商', value: 'supplier'"],
    [/label: '请输入备注信[^']*?\n/g, "label: '请输入备注信息'\n"],
  ],
  'fund/OtherReceiptDetail.vue': [
    [/label: '其它收入[^']*?, value: 'ice'/g, "label: '其它收入单', value: 'ice'"],
    [/label: '其它支出[^']*?, value: 'oce'/g, "label: '其它支出单', value: 'oce'"],
  ],
}

// Global patterns across all report vue files
const globalPatterns = [
  // Broken label strings ending with ? or replacement char before newline
  [/label: '([^'\n]*?)[\uFFFD?], value:/g, (m, text) => {
    const fixes = {
      '全部供应': '全部供应商',
      '欠款供应': '欠款供应商',
      '供应': '供应商',
      '其它收入': '其它收入单',
      '其它支出': '其它支出单',
    }
    for (const [k, v] of Object.entries(fixes)) {
      if (text.startsWith(k) || text === k) return `label: '${v}', value:`
    }
    return `label: '${text}', value:`
  }],
  [/label: '([^'\n]*?)[\uFFFD?]\s*\n/g, (m, text) => {
    const fixes = {
      '请输入单位名': '请输入单位名称',
      '请输入单位编': '请输入单位编号',
      '请输入备注信': '请输入备注信息',
    }
    for (const [k, v] of Object.entries(fixes)) {
      if (text.startsWith(k)) return `label: '${v}'\n`
    }
    return `label: '${text}'\n`
  }],
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
  const rel = path.relative(reportDir, file).replace(/\\/g, '/')

  if (fileFixes[rel]) {
    for (const [re, rep] of fileFixes[rel]) {
      s = s.replace(re, rep)
    }
  }

  for (const [re, rep] of globalPatterns) {
    if (typeof rep === 'function') s = s.replace(re, rep)
    else s = s.replace(re, rep)
  }

  if (s !== orig) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed:', rel)
    total++
  }
}
console.log('done, files fixed:', total)
