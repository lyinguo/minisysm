import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const reportDir = path.join(path.dirname(fileURLToPath(import.meta.url)), '../src/views/report')

function walk(dir, files = []) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name)
    if (fs.statSync(p).isDirectory()) walk(p, files)
    else if (name.endsWith('.vue')) files.push(p)
  }
  return files
}

const fixes = [
  [/value: '采购[^']* },/g, "value: '采购单' },"],
  [/value: '销售[^']* },/g, "value: '销售单' },"],
  [/label: '核销状[^']*,/g, "label: '核销状态',"],
]

for (const file of walk(reportDir)) {
  let s = fs.readFileSync(file, 'utf8')
  const orig = s
  for (const [p, r] of fixes) s = s.replace(p, r)
  if (s !== orig) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed', path.basename(file))
  }
}
