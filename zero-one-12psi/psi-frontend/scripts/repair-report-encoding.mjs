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
  // template: broken label attributes (missing closing quote)
  [/label="辅助属[^"]* width="/g, 'label="辅助属性" width="'],
  [/label="所属组[^"]* width="/g, 'label="所属组织" width="'],
  [/label="供应[^"]* width="/g, 'label="供应商" width="'],
  [/label="入库状[^"]* width="/g, 'label="入库状态" width="'],
  [/label="未入库数[^"]* width="/g, 'label="未入库数量" width="'],
  [/label="未入库金[^"]* width="/g, 'label="未入库金额" width="'],
  [/label="应收款余[^"]* width="/g, 'label="应收款余额" width="'],
  [/label="应付款余[^"]* width="/g, 'label="应付款余额" width="'],
  [/label="收款[^"]* width="/g, 'label="收款率" width="'],
  [/label="付款[^"]* width="/g, 'label="付款率" width="'],
  [/label="核销状[^"]* width="/g, 'label="核销状态" width="'],
  [/label="折扣[^"]* width="/g, 'label="折扣额" width="'],
  [/label="总成[^"]* width="/g, 'label="总成本" width="'],
  [/prop="grossProfitRate" label="毛利[^"]* width="/g, 'prop="grossProfitRate" label="毛利率" width="'],
  [/prop="grossProfitMargin" label="毛利[^"]* width="/g, 'prop="grossProfitMargin" label="毛利率" width="'],
  [/label="毛利[^"]* width="/g, 'label="毛利润" width="'],
  [/label="制单[^"]* width="/g, 'label="制单人" width="'],

  // script: broken strings
  [/return '已入[^']*'/g, "return '已入库'"],
  [/return '未入[^']*'/g, "return '未入库'"],
  [/加载采购订单跟踪表失[^']*'\)/g, "加载采购订单跟踪表失败')"],
  [/已刷新数[^']*'\)/g, "已刷新数据')"],
  [/ElMessage\.success\('搜索完成'\)/g, "ElMessage.success('搜索完成')"],

  // script: merged lines (newline eaten by encoding corruption)
  [/表格数[^c]*const currentTableData/g, '表格数据\nconst currentTableData'],
  [/设置默认排序[^"]*"单据排序"/g, '设置默认排序为"单据排序"'],
  [/仓库搜索弹[^c]*const searchConfig/g, '仓库搜索弹窗\nconst searchConfig'],
  [/仓库搜[^i]*  inline: false/g, '仓库搜索\n  inline: false'],
  [/搜索事[^c]*const handleGoodSearch/g, '搜索事件\nconst handleGoodSearch'],
  [/数据结[^c]*const transformToProductStructure/g, '数据结构\nconst transformToProductStructure'],
  [/仓库分[^c]*  const productGroups/g, '仓库分组\n  const productGroups'],
  [/根数据一[^p]*        productName/g, '根数据一致\n        productName'],
  [/过滤供应[^i]*      if \(formData\.supplier/g, '过滤供应商\n      if (formData.supplier'],
  [/进行排[^f]*    filteredData\.sort/g, '进行排序\n    filteredData.sort'],
  [/显示的数[^c]*  currentTableData\.value = filteredData/g, '显示的数据\n  currentTableData.value = filteredData'],
  [/重置到第一[^}]*\}/g, '重置到第一页\n}'],
  [/父级行[^c]*const total = computed/g, '父级行）\nconst total = computed'],
  [/父级行[^c]*const currentPageData = computed/g, '父级行）\nconst currentPageData = computed'],
  [/汇总信[^c]*const getDateRange/g, '汇总信息\nconst getDateRange'],
  [/初始[^o]*onMounted\(\(\) => \{/g, '初始化\nonMounted(() => {'],

  // export object keys
  [/        辅助属[^:]* /g, '        辅助属性: '],
  [/        所属组[^:]* /g, '        所属组织: '],
  [/        供应[^:]* /g, '        供应商: '],
  [/        入库状[^:]* /g, '        入库状态: '],
  [/        未入库数[^:]* /g, '        未入库数量: '],
  [/        未入库金[^:]* /g, '        未入库金额: '],

  // comments in template
  [/列顺[^<]*-->/g, '列顺序 -->'],
  [/商品名称[^<]*-->/g, '商品名称列 -->'],
  [/仓库[^<]*-->/g, (match) => (match.includes('el-table') ? match : '仓库列 -->')],

  // misc UI text
  [/操作按钮[^<]*-->/g, '操作按钮 -->'],
]

let fixedCount = 0
for (const file of walk(reportDir)) {
  const original = fs.readFileSync(file, 'utf8')
  let content = original
  for (const [pattern, replacement] of replacements) {
    content = content.replace(pattern, replacement)
  }
  if (content !== original) {
    fs.writeFileSync(file, content, 'utf8')
    fixedCount++
    console.log('repaired:', path.relative(reportDir, file))
  }
}
console.log(`done, ${fixedCount} files repaired`)
