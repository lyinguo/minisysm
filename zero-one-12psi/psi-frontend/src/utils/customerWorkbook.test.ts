import { describe, it, expect } from 'vitest'
import { utils, write } from 'xlsx'
import { customerHeaders, parseCustomerWorkbook } from './customerWorkbook'

function workbook(rows: unknown[][]): ArrayBuffer {
  const book = utils.book_new()
  utils.book_append_sheet(book, utils.aoa_to_sheet(rows), '客户')
  return write(book, { type: 'array', bookType: 'xlsx' })
}
describe('customer Excel import', () => {
  it('preserves leading zeroes, contacts and banking fields', () => {
    const rows = parseCustomerWorkbook(workbook([customerHeaders, ['001', '客户', '', '', '联系人', '00123', '地址', '银行', '00012', '税号', '备注']]))
    expect(rows[0]).toMatchObject({ number: '001', category: '常规类别', bank_account: '00012', remark: '备注', contacts: [{ name: '联系人', phone: '00123', address: '地址', isMain: true }] })
  })
  it('rejects another module template', () => {
    expect(() => parseCustomerWorkbook(workbook([['供应商编号', '供应商名称']]))).toThrow('表头不匹配')
  })
  it('rejects missing required fields and duplicate codes', () => {
    expect(() => parseCustomerWorkbook(workbook([customerHeaders, ['001', '']]))).toThrow('必填')
    expect(() => parseCustomerWorkbook(workbook([customerHeaders, ['001', '甲'], ['001', '乙']]))).toThrow('重复')
  })
  it('rejects an empty template', () => {
    expect(() => parseCustomerWorkbook(workbook([customerHeaders]))).toThrow('1 至 500')
  })
})
