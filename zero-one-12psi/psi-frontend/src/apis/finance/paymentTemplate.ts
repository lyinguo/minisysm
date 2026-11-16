import * as XLSX from 'xlsx'
import type { PaymentImportRow } from './paymentWorkflow'

export const paymentTemplateHeaders = ['付款单编号', '付款日期', '供应商编号', '结算账户编号', '付款金额', '结算号', '单据备注', '明细备注']

export function paymentTemplateBook() {
  const book = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet([paymentTemplateHeaders]), '付款模板')
  XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet([
    ['填写说明'],
    ['在付款模板工作表第2行开始填写，每行代表一条实际付款账户明细。'],
    ['同一付款单编号的多行会合并成一张草稿，供应商、付款日期和单据备注必须一致。'],
    ['供应商编号、结算账户编号应从系统基础资料中查询，填写编号，不要填写名称或内部ID。'],
    ['付款日期填写文本YYYY-MM-DD，例如2026-11-15；编号列建议在Excel中设为文本以保留前导零。'],
    ['付款金额大于0，最多8位整数和4位小数；结算号、两种备注可留空。'],
    ['每批最多1000行、100张付款单；同一张单最多200条账户明细。'],
    ['上传后先预览核对，再确认整批保存草稿；不会自动扣款，需打开草稿核对原采购和退货抵扣后审核。'],
    ['任何一张单校验失败则整批不保存。不要填写公式，不要导入已存在的付款单编号。']
  ]), '填写说明')
  return book
}

export function parsePaymentTemplate(bytes: ArrayBuffer): PaymentImportRow[] {
  if (!bytes.byteLength || bytes.byteLength > 1024 * 1024) throw new Error('请选择非空模板文件，最大1MiB')
  const book = XLSX.read(bytes, { type: 'array', cellFormula: true })
  const sheet = book.Sheets['付款模板']
  if (!sheet) throw new Error('没有“付款模板”工作表，请下载本页面提供的模板')
  if (Object.values(sheet).some(cell => cell && typeof cell === 'object' && 'f' in cell)) throw new Error('模板不能包含公式，请粘贴为确定的文本或数值')
  const grid = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, raw: false, defval: '' })
  const headers = (grid.shift() || []).map(value => String(value).trim())
  if (headers.length !== paymentTemplateHeaders.length || headers.some((value, index) => value !== paymentTemplateHeaders[index])) throw new Error('模板列名或顺序不符，请使用本页面下载的付款模板')
  const rows = grid.filter(row => row.some(value => String(value).trim()))
  if (!rows.length || rows.length > 1000) throw new Error('请填写1到1000行付款数据')
  return rows.map((row, index) => {
    const cells = row.map(value => String(value ?? '').trim())
    if (cells.slice(8).some(Boolean)) throw new Error(`第${index + 2}行包含模板以外的数据列`)
    if (!cells[0] || !cells[2] || !cells[3]) throw new Error(`第${index + 2}行须填写付款单编号、供应商编号和结算账户编号`)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(cells[1])) throw new Error(`第${index + 2}行日期请按文本YYYY-MM-DD填写`)
    if (!/^\d{1,8}(\.\d{1,4})?$/.test(cells[4]) || Number(cells[4]) <= 0) throw new Error(`第${index + 2}行金额必须大于0，最多8位整数和4位小数`)
    return { number: cells[0], date: cells[1], supplierNumber: cells[2], accountNumber: cells[3], money: cells[4], settle: cells[5] || '', remark: cells[6] || '', lineRemark: cells[7] || '' }
  })
}
