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

for (const file of walk(reportDir)) {
  let s = fs.readFileSync(file, 'utf8')
  const before = s
  s = s.replace(/\/\/[^\n]*?  if \(anyRes/g, '// 兼容多种分页结构\n    if (anyRes')
  s = s.replace(/console\.log\('【([^']+)接口返回', res\)/g, "console.log('【$1接口返回】', res)")
  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed', path.basename(file))
  }
}
