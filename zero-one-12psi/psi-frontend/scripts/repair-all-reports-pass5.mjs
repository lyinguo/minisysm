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

const keyFixes = [
  [/所属组[^\s:,\n]*\s+item\./g, '所属组织: item.'],
  [/所属组[^\s:,\n]*\s+row\./g, '所属组织: row.'],
  [/供应[^\s:,\n]*\s+item\./g, '供应商: item.'],
  [/辅助属[^\s:,\n]*\s+item\./g, '辅助属性: item.'],
  [/折扣[^\s:,\n]*\s+item\./g, '折扣额: item.'],
  [/应付款余[^\s:,\n]*\s+item\./g, '应付款余额: item.'],
  [/付款[^\s:,\n]*\s+`\$\{/g, '付款率: `${'],
  [/核销状[^\s:,\n]*\s+item\./g, '核销状态: item.'],
  [/label="所属组[^"\n]*"/g, 'label="所属组织"'],
  [/label="所属组[^"\n]*\s*$/gm, 'label="所属组织"'],
]

for (const file of walk(reportDir)) {
  let s = fs.readFileSync(file, 'utf8')
  const before = s
  for (const [re, rep] of keyFixes) s = s.replace(re, rep)
  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed:', path.basename(file))
  }
}

console.log('pass5 done')
