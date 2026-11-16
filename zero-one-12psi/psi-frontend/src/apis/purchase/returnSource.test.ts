import { beforeEach, describe, expect, it, vi } from 'vitest'
const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => http }))
import { purchaseReturnSourceApi } from './returnSource'

describe('actual purchase return source transport', () => {
  beforeEach(() => vi.clearAllMocks())
  it('reads only persisted source information and preserves business rejection', async () => {
    http.get.mockResolvedValue({ code: 9995, message: '来源采购单未实际审核入账' })
    await expect(purchaseReturnSourceApi.preview('receipt')).rejects.toThrow('未实际审核入账')
    expect(http.get).toHaveBeenCalledWith('/j3-purchase/purchase-note/getBuildBre', { id: 'receipt' })
    expect(http.post).not.toHaveBeenCalled()
  })
  it('refuses a different source, missing snapshot or nonpositive allowance', async () => {
    for (const data of [{ source: 'other', sourceVersion: 'a'.repeat(64), items: [{ source: 'line', available: 1 }] }, { source: 'receipt', items: [] }, { source: 'receipt', sourceVersion: 'a'.repeat(64), items: [{ source: 'line', available: 0 }] }]) {
      http.get.mockResolvedValue({ code: 10000, data })
      await expect(purchaseReturnSourceApi.preview('receipt')).rejects.toThrow('信息不完整')
    }
  })
})
