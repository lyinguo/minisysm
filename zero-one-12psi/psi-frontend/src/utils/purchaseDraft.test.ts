import { describe, expect, it } from 'vitest'
import { purchaseEditorRows, purchaseEditorPayload, recalculatePurchaseRow } from './purchaseDraft'
import type { PurchaseDocument } from '@/apis/purchase/purchaseOrder/type'
function document(): PurchaseDocument {
  return { version: 'read-version', header: { id: 'document-uuid', supplier: 'supplier-uuid', time_text: '2026-11-15 13:47:00', money: 0 }, items: [{ id: 'line-uuid', source: 'source-line', goods: 'goods-uuid', goodsName: '真实商品', warehouse: 'warehouse-uuid', warehouseName: '真实仓库', unit: '个', price: 100, nums: 2, discount: 1, dsc: 0, total: 200, tax: .13, tat: 26, tpt: 226, batch: 'LOT', mfd: '2026-11-01', serial: '["SN1","SN2"]' }] }
}
describe('purchase editor persistence', () => {
  it('displays effective legacy rates and submits stable IDs, version and full metadata', () => {
    const source = document(), rows = purchaseEditorRows(source)
    expect(rows[0]).toMatchObject({ taxRate: 13, effectiveDiscount: 0, quantity: 2, warehouseName: '真实仓库' })
    rows[0].quantity = 3; recalculatePurchaseRow(rows[0])
    expect(rows[0]).toMatchObject({ amount: 300, taxAmount: 39, total: 339 })
    const payload = purchaseEditorPayload(source, { documentDate: '2026-11-15', documentNumber: 'BUY-QA' }, 'supplier-uuid', rows, { paidAmount: 0, documentAttachment: [] })
    expect(payload).toMatchObject({ id: 'document-uuid', version: 'read-version', time: '2026-11-15 13:47:00', money: 0 })
    expect(payload.details[0]).toMatchObject({ id: 'line-uuid', goods: 'goods-uuid', warehouse: 'warehouse-uuid', source: 'source-line', batch: 'LOT', mfd: '2026-11-01', serial: '["SN1","SN2"]', tax: 13, discount: 0 })
    expect(payload.account).toBeUndefined(); expect(payload.people).toBeUndefined(); expect(payload.file).toBeUndefined()
  })
  it('keeps four-decimal amounts and effective discounts without borrowing another document totals', () => {
    const source = document(); source.items[0] = { ...source.items[0], discount: .96, dsc: 9, total: 191, tax: .10, tat: 18.145, tpt: 209.145 }
    const row = purchaseEditorRows(source)[0]
    expect(row).toMatchObject({ taxRate: 9.5, effectiveDiscount: 4.5 })
    row.quantity = 3; recalculatePurchaseRow(row)
    expect(row).toMatchObject({ amount: 286.5, taxAmount: 27.2175, total: 313.7175 })
  })
  it('preserves original attachment metadata and calendar date retains the original time', () => {
    const source = document(); source.header.file = '[{"name":"凭证","url":"/proof","extra":"keep"}]'
    const payload = purchaseEditorPayload(source, { documentDate: '2026-11-16', documentNumber: 'BUY-QA' }, 'supplier-uuid', purchaseEditorRows(source), { paidAmount: 0, documentAttachment: [{ name: '凭证', url: '/proof', status: 'success' }] })
    expect(payload.time).toBe('2026-11-16 13:47:00'); expect(payload.file).toBe(source.header.file)
  })
  it('rejects failed attachments and payment without an account before sending the version', () => {
    const source = document(), rows = purchaseEditorRows(source), header = { documentDate: '2026-11-15', documentNumber: 'BUY-QA' }
    expect(() => purchaseEditorPayload(source, header, 'supplier-uuid', rows, { paidAmount: 1, documentAttachment: [] })).toThrow('结算账户')
    expect(() => purchaseEditorPayload(source, header, 'supplier-uuid', rows, { documentAttachment: [{ name: '失败附件', status: 'fail' }] })).toThrow('附件尚未上传成功')
  })
})
