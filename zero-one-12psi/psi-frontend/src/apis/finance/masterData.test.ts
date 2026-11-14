import { describe, it, expect, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ pendingBills: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => ({}) }))
vi.mock('@/apis/finance', () => ({ WriteoffAPI: mocks }))
import { loadWriteoffDocuments } from './masterData'

describe('pending writeoff documents', () => {
  it('retains real source IDs and sends actual filters for all document types', async () => {
    mocks.pendingBills.mockResolvedValue({ code: 10000, data: { rows: [{ id: 'real-document', number: 'DOC001', total: 10, anwo: 4 }] } })
    const rows = await loadWriteoffDocuments({ number: 'DOC001' })
    expect(rows).toHaveLength(4)
    expect(rows[0]).toMatchObject({ source: 'real-document', 单据编号: 'DOC001', 未核销金额: 4 })
    expect(mocks.pendingBills).toHaveBeenCalledWith(expect.objectContaining({ number: 'DOC001', type2: 0 }))
  })
  it('never replaces a failed query with demo data', async () => {
    mocks.pendingBills.mockResolvedValue({ code: 9999 })
    await expect(loadWriteoffDocuments()).rejects.toThrow('加载失败')
  })
})
