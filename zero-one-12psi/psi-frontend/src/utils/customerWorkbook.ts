import { read, utils, writeFileXLSX } from 'xlsx'

export const customerHeaders = ['客户编号', '客户名称', '客户类别', '客户等级', '联系人', '联系电话', '联系地址', '开户银行', '银行账号', '纳税号码', '备注']

export function downloadCustomerTemplate() {
  const book = utils.book_new()
  utils.book_append_sheet(book, utils.aoa_to_sheet([customerHeaders]), '客户')
  writeFileXLSX(book, '客户导入模板.xlsx')
}

export function parseCustomerWorkbook(bytes: ArrayBuffer) {
  const book = read(bytes, { type: 'array' })
  const sheet = book.Sheets[book.SheetNames[0]]
  if (!sheet) throw new Error('文件中没有工作表')
  const rows = utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '', raw: false, blankrows: false })
  if (customerHeaders.some((title, index) => rows[0]?.[index] !== title)) throw new Error('表头不匹配，请重新下载客户导入模板，不要修改列名或顺序')
  const data = rows.slice(1).filter(row => row.some(cell => String(cell).trim()))
  if (!data.length || data.length > 500) throw new Error('每次请填写 1 至 500 条客户数据')
  const numbers = new Set<string>()
  return data.map((row, index) => {
    const values = customerHeaders.map((_, column) => String(row[column] ?? '').trim())
    const [number, name, category, level, contact, phone, address, bank, account, tax, remark] = values
    if (!number || !name) throw new Error(`第 ${index + 2} 行：客户编号和名称必填`)
    if (numbers.has(number)) throw new Error(`第 ${index + 2} 行：客户编号重复 ${number}`)
    numbers.add(number)
    if (values.some(value => value.length > 256)) throw new Error(`第 ${index + 2} 行：字段内容过长`)
    return {
      number, name, category: category || '常规类别', level: level || '常规等级',
      bank_name: bank, bank_account: account, tax_number: tax, remark,
      contacts: contact || phone || address ? [{ name: contact, phone, address, isMain: true }] : []
    }
  })
}

export function exportCustomers(rows: Record<string, any>[]) {
  const book = utils.book_new()
  utils.book_append_sheet(book, utils.json_to_sheet(rows.map(row => ({
    客户编号: row.code ?? row.number ?? '', 客户名称: row.name ?? '', 客户类别: row.category ?? '',
    客户等级: row.level ?? row.grade ?? '', 备注: row.remark ?? row.memo ?? ''
  }))), '客户')
  writeFileXLSX(book, '客户数据.xlsx')
}
