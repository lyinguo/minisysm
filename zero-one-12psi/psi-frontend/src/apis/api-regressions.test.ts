import { beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ get: vi.fn(), delete: vi.fn(), request: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => mocks, DataUpType: { json: 1 } }))
import { PurchaseOrderAPI } from './purchase/PurchaseBooking/order'
import { SupplierAPI } from './basicdata/supplier'
import request from './openapi-ts-request-shim'
import { getOrgTree } from './common'

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
