import { describe, expect, it } from 'vitest'
import * as XLSX from 'xlsx'
import { parsePaymentTemplate, paymentTemplateBook, paymentTemplateHeaders } from './paymentTemplate'

function workbook(rows: unknown[][], formula = false) {
  const book = paymentTemplateBook()
  book.Sheets['付款模板'] = XLSX.utils.aoa_to_sheet([paymentTemplateHeaders, ...rows])
  if (formula) book.Sheets['付款模板']['E2'] = { t: 'n', v: 10, f: '5+5' }
  return XLSX.write(book, { type: 'array', bookType: 'xlsx' }) as ArrayBuffer
}
const row = ['PAY001', '2026-11-15', '000123', '000456', '0.0001', '', '同一单备注', '明细备注']

describe('真实付款模板工作簿', () => {
  it('生成带填写说明的空模板，并要求用户填入数据', () => {
    const book = paymentTemplateBook()
    expect(book.SheetNames).toEqual(['付款模板', '填写说明'])
    expect(XLSX.utils.sheet_to_json(book.Sheets['填写说明'], { header: 1 })).toContainEqual([expect.stringContaining('不会自动扣款')])
    expect(() => parsePaymentTemplate(XLSX.write(book, { type: 'array', bookType: 'xlsx' }))).toThrow('1到1000行')
  })
  it('解析实际XLSX字节，保留编号前导零和四位小数，同单多行交由服务端核对分组', () => {
    const parsed = parsePaymentTemplate(workbook([row, [...row.slice(0, 4), '10', ...row.slice(5)]]))
    expect(parsed).toHaveLength(2)
    expect(parsed[0]).toMatchObject({ number: 'PAY001', supplierNumber: '000123', accountNumber: '000456', money: '0.0001', settle: '' })
    expect(parsed[1].money).toBe('10')
  })
  it('拒绝公式、无效日期格式、金额精度及空白必填编号', () => {
    expect(() => parsePaymentTemplate(workbook([row], true))).toThrow('公式')
    for (const [index, value] of [[1, '11/15/26'], [4, '0.00001'], [4, '-1'], [4, '0'], [2, '']] as const) {
      const invalid = [...row]; invalid[index] = value
      expect(() => parsePaymentTemplate(workbook([invalid]))).toThrow()
    }
  })
  it('拒绝列名错位、超过1000行和超出大小限制的文件', () => {
    const book = paymentTemplateBook();book.Sheets['付款模板'] = XLSX.utils.aoa_to_sheet([['供应商名称'], ['错位']])
    expect(() => parsePaymentTemplate(XLSX.write(book, { type: 'array', bookType: 'xlsx' }))).toThrow('列名或顺序')
    expect(() => parsePaymentTemplate(workbook(Array.from({ length: 1001 }, () => row)))).toThrow('1到1000行')
    expect(() => parsePaymentTemplate(new ArrayBuffer(1024 * 1024 + 1))).toThrow('1MiB')
  })
})
