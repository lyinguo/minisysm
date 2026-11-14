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

function repair(content) {
  let s = content

  // comment merged with const/function on same line
  s = s.replace(/\/\/([^\n]*?)(?:\uFFFD|\?)?(const |function |async function )/g, '// $1\n$2')

  // comment merged with showX: in object
  s = s.replace(/\/\/ ([^\n]*?)(?:\?||)(  show)/g, '// $1\n$2')

  // interface fields merged on one line
  s = s.replace(/(\w+: [^;\n]+)(?:\?||)(  \w+:)/g, '$1\n$2')

  // ref declarations merged
  s = s.replace(/(ref<[^>]+>\(\[\]\)) \/\/ [^\n]*?(const \w+ = ref)/g, '$1\n$2')

  // remaining 采购 broken strings (replacement char variants)
  s = s.replace(/'采购.\) t = 1/g, "'采购单') t = 1")
  s = s.replace(/: '采购.,/g, ": '采购单',")
  s = s.replace(/item\.type === 0 \? '采购退货单' : '采购.,/g, "item.type === 0 ? '采购退货单' : '采购单',")

  // merged supplierName line in map
  s = s.replace(/\/\/ 供应.        supplierName:/g, '// 供应商\n        supplierName:')
  s = s.replace(/\/\/ 辅助属.        auxiliaryAttr:/g, '// 辅助属性\n        auxiliaryAttr:')

  // broken console.log still merged
  s = s.replace(/\/\/ 再打印一下[^\n]*console\.log\('【解析后. rows., list/g, "console.log('【解析后 rows】', list")

  // filter broken 采购
  s = s.replace(/item\.orderType === '采购.\)/g, "item.orderType === '采购单')")

  return s
}

for (const file of walk(reportDir)) {
  const original = fs.readFileSync(file, 'utf8')
  const fixed = repair(original)
  if (fixed !== original) {
    fs.writeFileSync(file, fixed, 'utf8')
    console.log('fixed:', path.basename(file))
  }
}

console.log('pass2 done')
