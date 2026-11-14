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

const replacements = [
  [/if \(state === 2\) return '已入库'[^\n]*/g, "if (state === 2) return '已入库'\n  if (state === 0) return '未入库'"],
  [/设置默认排序.单据排序"/g, '设置默认排序为"单据排序"'],
  [/label="总成[^"\n]*\n/g, 'label="总成本"\n'],
  [/label="汇[^"]*" align="/g, 'label="汇总" align="'],
  [/bct: number\s*\/\/ 总成[^\n]*/g, 'bct: number  // 总成本'],
  [/动态仓库字[^\]]*\]/g, '动态仓库字段 wb_${id}]'],
  [/响应式数[^*]*\*\/\nconst searchForm/g, '响应式数据\n */\nconst searchForm'],
  [/商品库存余额[^)]*\)/g, "商品库存余额表')"],
  [/各仓库数[^\n]*\n\s*tableColumn/g, '各仓库数据\n    tableColumn'],
  [/汇总数[^\n]*\n\s*exportRow/g, '汇总数据\n    exportRow'],
  [/exportRow\['汇[^']*成本'\]/g, "exportRow['汇总-成本']"],
  [/exportRow\['汇[^']*数量'\]/g, "exportRow['汇总-数量']"],
  [/exportRow\['汇[^']*总成[^']*'\]/g, "exportRow['汇总-总成本']"],
  [/计算属性：总成[^*]*\*\/\nconst totalCost/g, '计算属性：总成本\n */\nconst totalCost'],
  [/\* 初始化\nonMounted/g, '* 初始化\n */\nonMounted'],
  [/格式化数[^*]*\*\/\nfunction formatNumber/g, '格式化数字\n */\nfunction formatNumber'],
  [/正在导出商品库存余额[^.]*\.\./g, '正在导出商品库存余额表...'],
  [/ElMessage\.success\('导出成功[^)]*\)/g, "ElMessage.success('导出成功')"],
]

for (const file of walk(reportDir)) {
  const original = fs.readFileSync(file, 'utf8')
  let content = original
  for (const [pattern, replacement] of replacements) {
    content = content.replace(pattern, replacement)
  }
  if (content !== original) {
    fs.writeFileSync(file, content, 'utf8')
    console.log('fixed:', path.relative(reportDir, file))
  }
}
