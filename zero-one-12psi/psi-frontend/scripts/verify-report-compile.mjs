import fs from 'fs'
import path from 'path'
import { parse } from '@vue/compiler-sfc'

const reportDir = 'D:/code/minsystem/zero-one-12psi/psi-frontend/src/views/report'
const errors = []

function walk(dir, files = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) walk(p, files)
    else if (e.name.endsWith('.vue')) files.push(p)
  }
  return files
}

for (const file of walk(reportDir)) {
  const source = fs.readFileSync(file, 'utf8')
  const { descriptor, errors: parseErrors } = parse(source, { filename: file })
  if (parseErrors.length) {
    errors.push({ file, msg: parseErrors.map((e) => e.message).join('; ') })
    continue
  }
  if (descriptor.template?.content) {
    try {
      const { baseParse } = await import('@vue/compiler-dom')
      baseParse(descriptor.template.content, { comments: true })
    } catch (e) {
      errors.push({ file, msg: e.message })
    }
  }
}

if (errors.length) {
  console.error('FAILED', errors.length)
  for (const e of errors) console.error(e.file, e.msg)
  process.exit(1)
}
console.log('All report vue files compile OK:', walk(reportDir).length)
