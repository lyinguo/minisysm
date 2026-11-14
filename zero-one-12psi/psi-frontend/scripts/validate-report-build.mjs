import { execSync } from 'child_process'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
const reportDir = path.join(root, 'src/views/report')

function walk(dir, files = []) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name)
    if (fs.statSync(p).isDirectory()) walk(p, files)
    else if (name.endsWith('.vue')) files.push(p)
  }
  return files
}

const globalFixes = [
  [/加载采购订单跟踪表失[^']*\)/g, "加载采购订单跟踪表失败')"],
  [/已刷新数[^']*\)/g, "已刷新数据')"],
  [/设置默认排序.单据排序"/g, '设置默认排序为"单据排序"'],
  [/value: '采购[^']* },/g, "value: '采购单' },"],
  [/label: '核销状[^']*,/g, "label: '核销状态',"],
  [/placeholder="单据开始日期""YYYY-MM-DD"/g, 'placeholder="单据开始日期"\n                    value-format="YYYY-MM-DD"'],
  [/placeholder="单据结束日期""/g, 'placeholder="单据结束日期"\n                    value-format="YYYY-MM-DD"'],
  [/<el-option label="按商品 value="product" \/>/g, '<el-option label="按商品" value="product" />'],
  [/placeholder="请输入商品名[^\n"]*/g, 'placeholder="请输入商品名称"'],
  [/placeholder="请选择供应[^\n"]*/g, 'placeholder="请选择供应商"'],
]

function applyFixes() {
  let changed = 0
  for (const file of walk(reportDir)) {
    let s = fs.readFileSync(file, 'utf8')
    const orig = s
    for (const [p, r] of globalFixes) s = s.replace(p, r)
    if (s !== orig) {
      fs.writeFileSync(file, s, 'utf8')
      changed++
    }
  }
  return changed
}

for (let i = 0; i < 5; i++) {
  applyFixes()
  try {
    execSync('npm run build-only', { cwd: root, stdio: 'pipe', encoding: 'utf8' })
    console.log('BUILD SUCCESS')
    process.exit(0)
  } catch (e) {
    const out = (e.stdout || '') + (e.stderr || '')
    const m = out.match(/src\/views\/report\/[^\s:]+\.vue/)
    console.log(`build failed attempt ${i + 1}:`, m?.[0] || 'unknown')
    if (!m) {
      console.log(out.slice(-2000))
      process.exit(1)
    }
  }
}
process.exit(1)
