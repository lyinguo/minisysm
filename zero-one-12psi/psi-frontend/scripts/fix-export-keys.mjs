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

for (const file of walk('D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report')) {
  let s = fs.readFileSync(file, 'utf8')
  const before = s
  s = s.replace(/'制单[^']*':/g, "'制单人':")
  s = s.replace(/'属[^']*':/g, "'属性':")
  s = s.replace(/'折扣[^']*':/g, "'折扣额':")
  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed keys', path.basename(file))
  }
}
