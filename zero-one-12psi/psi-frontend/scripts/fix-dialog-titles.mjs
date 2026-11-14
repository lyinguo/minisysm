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
  s = s.replace(/title="供应商搜[^"\n]*\n/g, 'title="供应商搜索"\n')
  s = s.replace(/title="仓库搜[^"\n]*\n/g, 'title="仓库搜索"\n')
  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed', path.basename(file))
  }
}
