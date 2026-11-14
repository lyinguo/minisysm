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

const placeholderFixes = [
  [/placeholder="请选择筛选类型"/g, 'placeholder="请选择筛选类型"'],
  [/placeholder="请输入商品名[^\n"]*/g, 'placeholder="请输入商品名称"'],
  [/placeholder="请选择供应[^\n"]*/g, 'placeholder="请选择供应商"'],
  [/placeholder="请输入商品编[^\n"]*/g, 'placeholder="请输入商品编号"'],
  [/placeholder="开始日[^\n"]*/g, 'placeholder="开始日期"'],
  [/placeholder="结束日[^\n"]*/g, 'placeholder="结束日期"'],
  [/placeholder="单据开始日[^\n"]*/g, 'placeholder="单据开始日期"'],
  [/placeholder="单据结束日[^\n"]*/g, 'placeholder="单据结束日期"'],
]

// Fix broken placeholder missing closing quote on same line
const inlineFixes = [
  [/placeholder="请输入商品名[^"]* clearable/g, 'placeholder="请输入商品名称" clearable'],
  [/placeholder="请输入商品编[^"]* clearable/g, 'placeholder="请输入商品编号" clearable'],
]

for (const file of walk(reportDir)) {
  let s = fs.readFileSync(file, 'utf8')
  const orig = s
  for (const [p, r] of placeholderFixes) s = s.replace(p, r)
  for (const [p, r] of inlineFixes) s = s.replace(p, r)
  // multiline: placeholder broken at EOL before clearable on next line
  s = s.replace(/placeholder="请输入商品名[^\n"]*\n(\s*)clearable/g, 'placeholder="请输入商品名称"\n$1clearable')
  s = s.replace(/placeholder="请选择供应[^\n"]*\n(\s*)readonly/g, 'placeholder="请选择供应商"\n$1readonly')
  if (s !== orig) {
    fs.writeFileSync(file, s, 'utf8')
    console.log('fixed:', path.relative(reportDir, file))
  }
}
