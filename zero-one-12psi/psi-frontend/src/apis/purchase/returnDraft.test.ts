import { beforeEach, describe, expect, it, vi } from 'vitest'
const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => http }))
import { returnDraftApi } from './returnDraft'
const input = { source: 'source', sourceVersion: 'b'.repeat(64), number: '退货', time: '2026-11-16 12:00:00', money: 0, cost: 0, account: '', data: '', details: [{ source: 'original-line', nums: 1 }] }
describe('purchase return persisted transport', () => {
  beforeEach(() => vi.clearAllMocks())
  it('posts stock and financial transitions through PUT using the complete frozen versions', async () => {
    const versions = { a: 'c'.repeat(64), b: 'd'.repeat(64) }
    http.put.mockResolvedValue({ code: 10000, data: 2 })
    expect(await returnDraftApi.post(['a', 'b'], 1, versions)).toBe(2)
    expect(http.put).toHaveBeenCalledWith('/j3-purchase/purchase-return-form/approve', { ids: ['a', 'b'], status: 1, versions })
    await expect(returnDraftApi.post(['a', 'b'], 0, { a: versions.a })).rejects.toThrow('全部选中')
    expect(http.put).toHaveBeenCalledTimes(1); expect(http.get).not.toHaveBeenCalled()
  })
  it('requires a complete frozen review map and never refreshes after refusal', async () => {
    await expect(returnDraftApi.review(['a', 'b'], 1, { a: 'c'.repeat(64) })).rejects.toThrow('全部选中')
    expect(http.post).not.toHaveBeenCalled()
    http.post.mockResolvedValue({ code: 9995, message: '版本已变化' })
    await expect(returnDraftApi.review(['a'], 1, 'c'.repeat(64))).rejects.toThrow('版本已变化')
    expect(http.get).not.toHaveBeenCalled()
    expect(http.post).toHaveBeenCalledWith('/j3-purchase/purchase-return-form/checkout', { ids: ['a'], status: 1, versions: { a: 'c'.repeat(64) } })
  })
  it('updates the actual UUID endpoint with frozen source and draft versions', async () => {
    const body = { ...input, id: 'a'.repeat(32), version: 'c'.repeat(64) }
    http.put.mockResolvedValue({ code: 10000, data: body.id })
    expect(await returnDraftApi.save(body)).toBe(body.id)
    expect(http.put).toHaveBeenCalledWith('/j3-purchase/purchase-return-form/document/' + body.id, body)
    expect(http.get).not.toHaveBeenCalled()
  })
  it('does not treat legacy success text as a saved document', async () => {
    http.post.mockResolvedValue({ code: 10000, data: '新增成功' })
    await expect(returnDraftApi.save(input)).rejects.toThrow('先查询保存结果')
  })
  it('preserves server rejection and sends current draft identity for reserved-source account choices', async () => {
    http.post.mockResolvedValue({ code: 9995, message: '来源已变化' })
    await expect(returnDraftApi.save(input)).rejects.toThrow('来源已变化')
    http.get.mockResolvedValue({ code: 10000, data: [] })
    await returnDraftApi.accounts('source', '银行', true, 'draft')
    expect(http.get).toHaveBeenCalledWith('/j3-purchase/purchase-return-form/accounts', { source: 'source', keyword: '银行', updating: true, draft: 'draft' })
  })
})
