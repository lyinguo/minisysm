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

/** 修复损坏的字符串与合并行 */
const fixes = [
  [/加载采购订单跟踪表失[^']*'\)/g, "加载采购订单跟踪表失败')"],
  [/已刷新数[^']*'\)/g, "已刷新数据')"],
  [/设置默认排序.单据排序"/g, '设置默认排序为"单据排序"'],
  [/加载收发汇总失[^']*'\)/g, "加载收发汇总失败')"],
  [/exportRow\['汇[^']*总成[^']*\]/g, "exportRow['汇总-总成本']"],
  [/'汇[^']*总成[^']*:/g, "'汇总-总成本':"],
  [/'期初-总成[^']*:/g, "'期初-总成本':"],
  [/'采购[^']*成本'/g, "'采购单-成本'"],
  [/'采购[^']*数量'/g, "'采购单-数量'"],
  [/'采购[^']*总成[^']*:/g, "'采购单-总成本':"],
  [/'采购退货单-总成[^']*:/g, "'采购退货单-总成本':"],
  [/'销售单-总成[^']*:/g, "'销售单-总成本':"],
  [/'销售退货单-总成[^']*:/g, "'销售退货单-总成本':"],
  [/'调拨[^']*成本'/g, "'调拨单-出-成本'"],
  [/'调拨[^']*数量'/g, "'调拨单-出-数量'"],
  [/'调拨[^']*总成[^']*:/g, "'调拨单-出-总成本':"],
  [/'其它入库[^']*成本'/g, "'其它入库单-成本'"],
  [/'其它入库[^']*数量'/g, "'其它入库单-数量'"],
  [/'其它入库[^']*总成[^']*:/g, "'其它入库单-总成本':"],
  [/'其它出库[^']*成本'/g, "'其它出库单-成本'"],
  [/'其它出库[^']*数量'/g, "'其它出库单-数量'"],
  [/'其它出库[^']*总成[^']*:/g, "'其它出库单-总成本':"],
  [/'汇[^']*成本'/g, "'汇总-成本'"],
  [/'汇[^']*数量'/g, "'汇总-数量'"],
  [/'入库-总成[^']*:/g, "'入库-总成本':"],
  [/'出库-总成[^']*:/g, "'出库-总成本':"],
  [/'所属组[^']*:/g, "'所属组织':"],
  [/'往来单[^']*:/g, "'往来单位':"],
  [/'辅助属[^']*:/g, "'辅助属性':"],
  [/label: '采购[^']*,/g, "label: '采购单',"],
  [/label: '调拨[^']*,/g, "label: '调拨单-出',"],
  [/label: '其它入库[^']*,/g, "label: '其它入库单',"],
  [/label: '其它出库[^']*,/g, "label: '其它出库单',"],
  [/label: '核销状[^']*,/g, "label: '核销状态',"],
  [/const exportFileName = ref\('商品收发明细[^']*\)/g, "const exportFileName = ref('商品收发明细表')"],
  [/正在导出商品收发明细[^.]*\.\./g, '正在导出商品收发明细表...'],
  [/获取销售汇总失[^']*,/g, "获取销售汇总失败',"],
  [/获取销售汇总失[^']*\)/g, "获取销售汇总失败')"],
  [/导出销售汇总失[^']*,/g, "导出销售汇总失败',"],
  [/导出销售汇总失[^']*\)/g, "导出销售汇总失败')"],
  [/数据已刷[^']*\)/g, "数据已刷新')"],
  [/已重置搜索条[^']*\)/g, "已重置搜索条件')"],
  [/未识别的分页结[^']*,/g, "未识别的分页结构',"],
  [/placeholder="单据开始日[^"]*"/g, 'placeholder="单据开始日期"'],
  [/unitType: '销售单[^']*,/g, "unitType: '销售单据',"],
  [/辅助属[^/]*\/\/ 辅助属/g, 'auxiliaryAttr: item.auxiliaryAttribute ?? \'\', // 辅助属性'],
  [/总成[^/]*\/\/ 总成/g, 'totalCost: Number(item.totalCost ?? 0), // 总成本'],
  [/毛利[^/]*\/\/ 毛利/g, 'grossProfit: Number(item.grossProfit ?? 0), // 毛利润'],
  [/计算字段禁用状[^c]*const /g, '计算字段禁用状态\nconst '],
  [/当前页[^c]*const originalTableData/g, '当前页）\nconst originalTableData'],
  [/保持原有行为[^c]*const showPersonColumn/g, '保持原有行为）\nconst showPersonColumn'],
  [/进行其他过[^ ]*  if/g, '进行其他过滤\n  if'],
  [/兼容后端返回 null\/undefined[^c]*const saleTotalAmount/g, '兼容后端返回 null/undefined）\nconst saleTotalAmount'],
  [/搜[^+]*\+ 导出共用[^c]*const buildCommonParams/g, '搜索 + 导出共用）\nconst buildCommonParams'],
  [/表格字段一[^ ]*  originalTableData/g, '表格字段一致\n    originalTableData'],
  [/展开成表格用的字[^ ]*  originalTableData/g, '展开成表格用的字段\n    originalTableData'],
  [/金额格式[^c]*const formatCurrency/g, '金额格式化\nconst formatCurrency'],
  [/加载一次数[^o]*onMounted/g, '加载一次数据\nonMounted'],
  [/双向绑定的数[^c]*const goodSearchForm/g, '双向绑定的数据\nconst goodSearchForm'],
  [/分页状[^=]*====/g, '分页状态\n// ===='],
  [/改变页[^每]*每页条数时重新请[^c]*const handleSizeChange/g, '改变页码/每页条数时重新请求\nconst handleSizeChange'],
  [/金额统[^<]*-->/g, '金额统计 -->'],
  [/添加各仓库数[^t]*tableColumn/g, '添加各仓库数据\n    tableColumn'],
  [/响应式数[^*]*\*\/\n/g, '响应式数据\n */\n'],
  [/按商[^?]*\?/g, '按商品'],
  [/供应[^/]*\/\/ 供应/g, "supplier: '', // 供应商"],
  [/开始日[^/]*\/\/ 结束日期/g, "startTime: '', // 开始日期\n  endTime: '' // 结束日期"],
  [/原逻辑保留[^=]*====/g, '原逻辑保留）\n// ===='],
  [/供应商弹窗控[^c]*const showSupplierDialog/g, '供应商弹窗控制\nconst showSupplierDialog'],
  [/后端 row[^ ]*前端表格[^c]*const mapBackendRowToItem/g, '后端 row -> 前端表格行\nconst mapBackendRowToItem'],
  [/接口返回[^']*,/g, "接口返回',"],
  [/当前条件下全部数[^ ]*pageIndex/g, '当前条件下全部数据\n      pageIndex'],
  [/列显示控[^=]*====/g, '列显示控制\n// ===='],
  [/拉一页数[^ ]*  fetchTableData/g, '拉一页数据\n  fetchTableData'],
  [/构造查询参[^&]*& 数据映射/g, '构造查询参数 & 数据映射'],
  [/从搜索表单构建后端查询参[^c]*const buildQueryParams/g, '从搜索表单构建后端查询参数\nconst buildQueryParams'],
  [/后端 row -> 前端表格[^c]*const mapBackendRowToItem/g, '后端 row -> 前端表格行\nconst mapBackendRowToItem'],
  [/搜索条件[^`]*`/g, (m) => m.includes('join') ? '搜索条件：${searchConditions.join(\'，\')}`' : m],
]

for (const file of walk(reportDir)) {
  let content = fs.readFileSync(file, 'utf8')
  const original = content
  for (const [pattern, replacement] of fixes) {
    content = content.replace(pattern, replacement)
  }
  if (content !== original) {
    fs.writeFileSync(file, content, 'utf8')
    console.log('fixed:', path.relative(reportDir, file))
  }
}
