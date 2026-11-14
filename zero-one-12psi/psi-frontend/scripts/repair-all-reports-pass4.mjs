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

  s = s.replace(/placeholder="([^"]*)"+/g, 'placeholder="$1"')
  s = s.replace(/label="采购[^"]*?\s+align="/g, 'label="采购单" align="')
  s = s.replace(/label="汇[^"]*?\s+align="/g, 'label="汇总" align="')
  s = s.replace(/value-format="YYYY-MM-DD""+/g, 'value-format="YYYY-MM-DD"')
  s = s.replace(/format="YYYY-MM-DD""+/g, 'format="YYYY-MM-DD"')

  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed:', path.basename(file))
  }
}

console.log('pass4 done')
