import fs from 'fs'
import path from 'path'

function walk(dir) {
  const files = []
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name)
    if (fs.statSync(full).isDirectory()) files.push(...walk(full))
    else if (name.endsWith('.vue')) files.push(full)
  }
  return files
}

const labelFixes = [
  [/label="制单[^\n"]*\n/g, 'label="制单人"\n'],
  [/label="属[^\n"]*\n/g, 'label="属性"\n'],
  [/label="折扣[^\n"]*\n/g, 'label="折扣额"\n'],
  [/label="应付款余[^\n"]*\n/g, 'label="应付款余额"\n'],
  [/label="应收款余[^\n"]*\n/g, 'label="应收款余额"\n'],
  [/label="增加应付[^\n"]*\n/g, 'label="增加应付款"\n'],
  [/label="增加预付[^\n"]*\n/g, 'label="增加预付款"\n'],
  [/label="增加应收[^\n"]*\n/g, 'label="增加应收款"\n'],
  [/label="增加预收[^\n"]*\n/g, 'label="增加预收款"\n'],
  [/label="供应[^\n"]*\n/g, 'label="供应商"\n'],
]

for (const file of walk('D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report')) {
  let s = fs.readFileSync(file, 'utf8')
  const before = s
  for (const [re, rep] of labelFixes) s = s.replace(re, rep)
  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed', path.basename(file))
  }
}

console.log('fund labels done')
