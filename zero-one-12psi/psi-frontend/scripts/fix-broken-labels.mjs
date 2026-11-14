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

const fixes = [
  [/label="辅助属[^\n"]*\n/g, 'label="辅助属性"\n'],
  [/label="往来单[^\n"]*\n/g, 'label="往来单位"\n'],
  [/label="所属组[^\n"]*\n/g, 'label="所属组织"\n'],
]

for (const file of walk('D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report')) {
  let s = fs.readFileSync(file, 'utf8')
  const before = s
  for (const [re, rep] of fixes) s = s.replace(re, rep)
  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed labels', path.basename(file))
  }
}
