import { describe, expect, it } from 'vitest'
import { purchaseEntryPayload, purchaseSelectionRows } from './purchaseEntry'

const header = { documentDate: '2026-11-15', documentNumber: 'QA-ENTRY' }
const row = { productName: '商品', goodsId: 'goods-uuid', warehouseId: 'warehouse-uuid', unit: 'unit', price: 100, quantity: 2, taxRate: 13 }
describe('procurement entry business payload', () => {
  it('retains every selected product and does not turn category into an attribute', () => {
    const rows = purchaseSelectionRows([{ id: 'a', name: '甲', category: '未分类', unit: 'unit' }, { id: 'b', name: '乙', category: '药品', attr: '蓝色', unit: 'unit' }])
    expect(rows.map(row => row.goodsId)).toEqual(['a', 'b'])
    expect(rows.map(row => row.attr)).toEqual(['', '蓝色'])
  })
  it('derives header and line amounts, retaining zero unpaid money and all attachment metadata', () => {
    const payload = purchaseEntryPayload(header, 'supplier-uuid', [row], { actualAmount: 0, documentCost: 226, paidAmount: 0, documentAttachment: [{ name: 'a', url: '/a', status: 'success' }, { name: 'b', url: '/b', status: 'success' }] })
    expect(payload.purchaseNoteBuyDTO).toMatchObject({ total: 200, actual: 226, money: 0, supplier: 'supplier-uuid' })
    expect(payload.purchaseNoteInfoDTOS[0]).toMatchObject({ goods: 'goods-uuid', warehouse: 'warehouse-uuid', total: 200, tat: 26, tpt: 226 })
    expect(JSON.parse(payload.purchaseNoteBuyDTO.file!)).toHaveLength(2)
  })
  it('rejects malformed money, overpayment and unfinished file uploads instead of recording zero', () => {
    expect(() => purchaseEntryPayload(header, 's', [row], { paidAmount: 'abc' })).toThrow('实付金额')
    expect(() => purchaseEntryPayload(header, 's', [{ ...row, quantity: '2abc' }], {})).toThrow('数量')
    expect(() => purchaseEntryPayload(header, 's', [{ ...row, price: '-1' }], {})).toThrow('单价')
    expect(() => purchaseEntryPayload(header, 's', [row], { paidAmount: 300, settlementAccount: 'a' })).toThrow('实付金额不能超过')
    expect(() => purchaseEntryPayload(header, 's', [row], { documentAttachment: [{ name: 'failed', status: 'fail' }] })).toThrow('附件尚未上传成功')
  })
})
