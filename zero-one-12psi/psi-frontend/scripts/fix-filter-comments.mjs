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
  s = s.replace(/\/\/ 过滤制单[^\n]*if \(formData\.user/g, '// 过滤制单人\n    if (formData.user')
  s = s.replace(/\/\/ 过滤关联人员[^\n]*if \(formData\.people/g, '// 过滤关联人员\n    if (formData.people')
  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed', path.basename(file))
  }
}
