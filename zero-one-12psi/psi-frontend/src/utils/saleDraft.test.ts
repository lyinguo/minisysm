import { describe, expect, it } from 'vitest'
import { saleEditorPayload, saleEditorRows } from './saleDraft'
import type { SaleDocumentDetail } from '@/apis/sales/order/type'

function fixture(): SaleDocumentDetail {
  return { version: 'server-version', header: { id: 'sale-real', frame: 'org-real', customer: 'customer-real', source: 'order-real', time: '2026-11-15T13:47:00', timeEpoch: Date.parse('2026-11-15T13:47:00+08:00'), number: 'XS-REAL', money: 99, more: '{"custom":"kept"}', invoice: 3, nucleus: 0 },
    items: [{ id: 'line-real', pid: 'sale-real', source: 'order-line', goods: 'goods-real', goodsName: '真实商品', goodsNumber: 'G-REAL', unit: '件', warehouse: 'warehouse-real', price: 100, nums: 2, total: 191, tax: .095, discount: .955, tat: 18.145, tpt: 209.145, batch: 'B-real', mfd: '2026-11-01', serial: '["S1","S2"]', data: '原备注' }] }
}
function header() { return { frame: 'org-real', documentDate: '2026-11-15', documentNumber: 'XS-REAL' } }

describe('sale draft editor contract', () => {
  it('preserves actual IDs, source links, batch/serial metadata and an explicitly unpaid amount', () => {
    const document = fixture()
    const rows = saleEditorRows(document)
    rows[0].quantity = 3
    const payload = saleEditorPayload(document, header(), 'customer-real', rows, { receivedAmount: 0, relatedPerson: 'person-real', settlementAccount: 'account-real', documentAttachment: [] })
    expect(payload).toMatchObject({ id: 'sale-real', version: 'server-version', source: 'order-real', money: 0, more: '{"custom":"kept"}', time: document.header.timeEpoch })
    expect(payload.items?.[0]).toMatchObject({ id: 'line-real', source: 'order-line', goods: 'goods-real', warehouse: 'warehouse-real', nums: 3, batch: 'B-real', mfd: '2026-11-01', serial: '["S1","S2"]' })
  })
  it('converts displayed percentage to the API fraction without losing a 9.5% tax rate', () => {
    const document = fixture()
    const rows = saleEditorRows(document)
    expect(rows[0].taxRate).toBe(9.5)
    expect(saleEditorPayload(document, header(), 'customer-real', rows, {}).items?.[0]).toMatchObject({ tax: .095, discount: .955 })
  })
  it('changes the chosen business date while retaining the existing time of day', () => {
    const document = fixture()
    const payload = saleEditorPayload(document, { ...header(), documentDate: '2026-11-16' }, 'customer-real', saleEditorRows(document), {})
    expect(payload.time).toBe(Date.parse('2026-11-16T13:47:00+08:00'))
  })
  it('retains every uploaded attachment and rejects an unfinished upload', () => {
    const document = fixture()
    const files = [{ name: 'a.pdf', url: '/a.pdf', status: 'success' }, { name: 'b.pdf', url: '/b.pdf', status: 'success' }]
    expect(JSON.parse(saleEditorPayload(document, header(), 'customer-real', saleEditorRows(document), { documentAttachment: files }).file!)).toHaveLength(2)
    expect(() => saleEditorPayload(document, header(), 'customer-real', saleEditorRows(document), { documentAttachment: [{ name: 'bad.pdf', status: 'fail' }] })).toThrow('附件尚未上传成功')
  })
})
