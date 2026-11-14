import { beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ get: vi.fn(), delete: vi.fn(), request: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => mocks, DataUpType: { json: 1 } }))
import { PurchaseOrderAPI } from './purchase/PurchaseBooking/order'
import { SupplierAPI } from './basicdata/supplier'
import request from './openapi-ts-request-shim'

describe('unfinished API actions', () => {
  beforeEach(() => vi.clearAllMocks())
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
})
