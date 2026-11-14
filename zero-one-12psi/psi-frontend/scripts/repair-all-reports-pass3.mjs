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

  s = s.replace(
    /console\.log\('【解析后[^']*rows[^']*, list, 'total =', totalCount\)/g,
    "console.log('【解析后 rows】', list, 'total =', totalCount)"
  )
  s = s.replace(
    /\/\/ 再打印一下[^\n]*console\.log\('【解析后[^']*rows[^']*, list, 'total =', totalCount\)/g,
    "console.log('【解析后 rows】', list, 'total =', totalCount)"
  )

  s = s.replace(
    /console\.log\('【[^']*导出接口返回', \{\s*type: 'application\/vnd\.openxmlformats-officedocument\.spreadsheetml\.sheet'\s*\}\)/g,
    "const exportRes: any = res\n    const blob: Blob = exportRes?.data ?? exportRes"
  )

  if (s !== before) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed:', path.basename(file))
  }
}

console.log('pass3 done')
