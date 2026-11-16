import { beforeEach, describe, expect, it, vi } from 'vitest'
const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => http }))
import { returnDraftApi } from './returnDraft'
const input = { source: 'a'.repeat(32), sourceVersion: 'b'.repeat(64), number: 'QA-RETURN', time: '2026-11-16 12:00:00', money: 0, cost: 0, account: '', data: '', salesReturnOrderInfos: [{ source: 'line-uuid', nums: 1 }] }
describe('persisted return draft transport', () => {
  beforeEach(() => vi.clearAllMocks())
  it('does not interpret a legacy success phrase as a persisted UUID', async () => { http.post.mockResolvedValue({ code: 10000, data: '新增成功', message: '操作成功' }); await expect(returnDraftApi.save(input)).rejects.toThrow('服务未返回有效退货单编号') })
  it('sends actual string source IDs and keeps business rejection visible', async () => { http.post.mockResolvedValue({ code: 9995, message: '来源已变化' }); await expect(returnDraftApi.save(input)).rejects.toThrow('来源已变化'); expect(http.post).toHaveBeenCalledWith('/sale/return/addSalesReturnOrder', input) })
  it('does not accept another document or a missing reviewed version as complete detail', async () => { http.get.mockResolvedValue({ code: 10000, data: { header: { id: 'other' }, version: 'a'.repeat(64) } }); await expect(returnDraftApi.document('target')).rejects.toThrow('数据不完整') })
})
