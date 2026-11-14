import { read, utils, writeFileXLSX } from 'xlsx'

export const warehouseHeaders = ['仓库编号', '仓库名称', '联系人', '联系电话', '仓库地址', '备注']
export const supplierHeaders = ['供应商编号', '供应商名称', '供应商类别', '增值税税率', '联系人', '联系电话', '联系地址', '开户银行', '银行账号', '纳税号码', '备注']
export const productHeaders = ['商品名称', '商品编号', '商品型号', '商品类别', '商品品牌', '商品单位', '购货价格', '销货价格', '零售价格', '兑换积分', '商品条码', '商品货位', '库存阈值', '商品类型', '备注信息']

export function downloadTemplate(headers: string[], filename: string) {
  const book = utils.book_new()
  utils.book_append_sheet(book, utils.aoa_to_sheet([headers]), '数据')
  writeFileXLSX(book, filename)
}

export function exportRecords(rows: Record<string, unknown>[], filename: string) {
  const book = utils.book_new()
  utils.book_append_sheet(book, utils.json_to_sheet(rows), '数据')
  writeFileXLSX(book, filename)
}

export function parseWarehouseWorkbook(bytes: ArrayBuffer) {
  const book = read(bytes, { type: 'array' })
  const sheet = book.Sheets[book.SheetNames[0]]
  if (!sheet) throw new Error('文件中没有工作表')
  const rows = utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '', raw: false, blankrows: false })
  if (warehouseHeaders.some((header, i) => rows[0]?.[i] !== header)) throw new Error('表头不匹配，请下载仓库导入模板')
  const data = rows.slice(1).filter(row => row.some(value => String(value).trim()))
  if (!data.length || data.length > 500) throw new Error('每次请填写 1 至 500 条仓库数据')
  const codes = new Set<string>()
  return data.map((row, i) => {
    const [number, name, contacts, tel, add, memo] = warehouseHeaders.map((_, index) => String(row[index] ?? '').trim())
    if (!number || !name) throw new Error(`第 ${i + 2} 行：仓库编号和名称必填`)
    if (codes.has(number)) throw new Error(`第 ${i + 2} 行：仓库编号重复`)
    codes.add(number)
    return { number, name, contacts, tel, add, data: memo }
  })
}
