import { beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), delete: vi.fn(), request: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => mocks, DataUpType: { json: 1 } }))
import { PurchaseOrderAPI } from './purchase/PurchaseBooking/order'
import { SupplierAPI } from './basicdata/supplier'
import request from './openapi-ts-request-shim'
import { getOrgTree } from './common'
import { SaleOrderApi } from './sales/order'
import { PurchaseNoteAPI } from './purchase/purchaseOrder'
import type { PurchaseNoteAddDTO } from './purchase/purchaseOrder/type'

describe('unfinished API actions', () => {
  beforeEach(() => vi.clearAllMocks())
  it('rejects a procurement business failure instead of reporting the draft saved', async () => {
    mocks.post.mockResolvedValue({ code: 9995, message: '采购单编号已被使用' })
    const body = {
      purchaseNoteBuyDTO: { supplier: 'supplier-uuid', people: '', account: '', time: '2026-11-15', number: 'PURCHASE-QA', money: 0, total: 100, actual: 100, cost: 0 },
      purchaseNoteInfoDTOS: [{ goods: 'goods-uuid', warehouse: 'warehouse-uuid', unit: 'unit', nums: 1, price: 100 }]
    } as PurchaseNoteAddDTO
    await expect(PurchaseNoteAPI.addPurchaseNote(body)).rejects.toThrow('采购单编号已被使用')
  })
  it.each(['b7dcd471c1ef4a4a911b06273e92156e', '12345678901234567890'])('preserves procurement string identifiers: %s', async supplier => {
    mocks.post.mockResolvedValue({ code: 10000, data: 'persisted-purchase-id' })
    const body = {
      purchaseNoteBuyDTO: { supplier, people: 'person-uuid', account: 'account-uuid', source: 'order-uuid', time: '2026-11-15', number: 'PURCHASE-QA', money: 0, total: 200, actual: 226, cost: 0 },
      purchaseNoteInfoDTOS: [{ goods: 'goods-uuid', warehouse: 'warehouse-uuid', unit: 'unit', mfd: '', serial: '["SN1","SN2"]', price: 100, nums: 2, tax: .13, total: 200, tpt: 226 }]
    } as PurchaseNoteAddDTO
    await PurchaseNoteAPI.addPurchaseNote(body)
    const payload = mocks.post.mock.calls[0][1]
    expect(payload.purchaseNoteBuyDTO).toMatchObject({ supplier, people: 'person-uuid', source: 'order-uuid' })
    expect(payload.purchaseNoteInfoDTOS[0]).toMatchObject({ goods: 'goods-uuid', warehouse: 'warehouse-uuid', mfd: '', serial: '["SN1","SN2"]' })
  })
  it('allows unpaid procurement without a person or account and requires an account for payment', async () => {
    const body = {
      purchaseNoteBuyDTO: { supplier: 'supplier-uuid', people: '', account: '', time: '2026-11-15', number: 'PURCHASE-QA', money: 0, total: 100, actual: 100, cost: 0 },
      purchaseNoteInfoDTOS: [{ goods: 'goods-uuid', warehouse: 'warehouse-uuid', unit: 'unit', nums: 1, price: 100 }]
    } as PurchaseNoteAddDTO
    mocks.post.mockResolvedValue({ code: 10000, data: 'persisted-purchase-id' })
    await PurchaseNoteAPI.addPurchaseNote(body)
    expect(mocks.post).toHaveBeenCalledTimes(1)
    body.purchaseNoteBuyDTO.money = 1
    await expect(PurchaseNoteAPI.addPurchaseNote(body)).rejects.toThrow('填写实付金额时请选择结算账户')
    expect(mocks.post).toHaveBeenCalledTimes(1)
  })
  it.each([true, false])('sends exact reviewed sales versions with every selected ID (target=%s)', async target => {
    const api = new SaleOrderApi()
    const ids = ['1234567890123456789', 'sale-uuid']
    mocks.post.mockResolvedValue({ code: 10000, data: 2 })
    const versions = Object.fromEntries(ids.map(id => [id, 'a'.repeat(64)]))
    await api.examineSales(ids, target, versions)
    expect(mocks.post).toHaveBeenCalledWith('/sale/form/examine', { ids, versions }, { params: { examine: target } })
    await api.checkSales(ids, target, versions)
    expect(mocks.post).toHaveBeenCalledWith('/sale/form/check', { ids, versions }, { params: { check: target } })
  })
  it('refuses incomplete or extra sales versions before transport', async () => {
    const api = new SaleOrderApi()
    await expect(api.checkSales(['a', 'b'], true, { a: 'a'.repeat(64) })).rejects.toThrow()
    await expect(api.examineSales(['a'], true, { a: 'a'.repeat(64), b: 'b'.repeat(64) })).rejects.toThrow()
    await expect(api.checkSales(['a', 'a'], true, { a: 'a'.repeat(64) })).rejects.toThrow()
    expect(mocks.post).not.toHaveBeenCalled()
  })
  it('sends sales deletion IDs in the array expected by the existing controller', async () => {
    mocks.delete.mockResolvedValue({ code: 10000, data: 1 })
    await new SaleOrderApi().deleteSales(['1234567890123456789'])
    expect(mocks.delete).toHaveBeenCalledWith('/sale/form/deleteSales', ['1234567890123456789'])
  })
  it('receives Excel export bytes as a Blob', async () => {
    mocks.request.mockResolvedValueOnce(new Blob(['excel']))
    await request('/j5-reportmanagement/procurement-payment-form/export', { method: 'GET' })
    expect(mocks.request).toHaveBeenCalledWith('GET', expect.any(String), expect.objectContaining({ responseType: 'blob' }))
  })
  it('preserves long string IDs when deleting purchase orders', async () => {
    mocks.delete.mockResolvedValueOnce({ code: 10000, data: '1' })
    await PurchaseOrderAPI.deletePurchaseOrders(['1234567890123456789'])
    expect(mocks.delete).toHaveBeenCalledWith(
      expect.stringContaining('/delete'),
      ['1234567890123456789'],
      expect.any(Object)
    )
  })
  it('fetches the supplier import template from the existing endpoint', async () => {
    mocks.get.mockResolvedValueOnce({ code: 10000, data: '/templates/supplier.xlsx' })
    const result = await SupplierAPI.downloadImportTemplate()
    expect(result.data).toBe('/templates/supplier.xlsx')
    expect(mocks.get).toHaveBeenCalledWith('/basic_information/supplier/template')
  })
  it('loads real organization nodes from the implemented basic-service route', async () => {
    const tree = [{ id: 'org-real', name: '实际组织', children: [] }]
    mocks.get.mockResolvedValueOnce({ code: 10000, data: tree })
    expect(await getOrgTree()).toEqual(tree)
    expect(mocks.get).toHaveBeenCalledWith('/basic_information/frame/getFrame')
  })
  it('does not treat an organization loading failure as an empty successful tree', async () => {
    mocks.get.mockResolvedValueOnce({ code: 9999, message: '组织服务暂不可用' })
    await expect(getOrgTree()).rejects.toThrow('组织服务暂不可用')
  })
})
