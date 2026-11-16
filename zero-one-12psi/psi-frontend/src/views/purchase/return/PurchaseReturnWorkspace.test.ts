import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus, { ElMessageBox } from 'element-plus'
const api = vi.hoisted(() => ({ getList: vi.fn(), getDocument: vi.fn(), preview: vi.fn(), list: vi.fn(), document: vi.fn(), sourceOptions: vi.fn(), accounts: vi.fn(), save: vi.fn(), review: vi.fn(), post: vi.fn() }))
vi.mock('@/apis/purchase/purchaseOrder', () => ({ PurchaseNoteAPI: api }))
vi.mock('@/apis/purchase/returnSource', () => ({ purchaseReturnSourceApi: api }))
vi.mock('@/apis/purchase/returnDraft', () => ({ returnDraftApi: api }))
import Workspace from './PurchaseReturnWorkspace.vue'
const id = 'a'.repeat(32), version = 'b'.repeat(64), sourceVersion = 'c'.repeat(64)
const item = { id: 'line', source: 'original', goodsName: '商品', nums: 1, available: 2, price: 100, tpt: 113, serial: '[]' }
async function render(query = '') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/purchase-return', component: { template: '<div />' } }] })
  await router.push('/purchase-return' + query)
  const wrapper = mount(Workspace, { global: { plugins: [router, ElementPlus], stubs: { ElDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /><slot name="footer" /></div>' } } } })
  await flushPromises(); return { wrapper, router }
}
async function click(wrapper: Awaited<ReturnType<typeof render>>['wrapper'], text: string) { await wrapper.findAll('button').find(b => b.text() === text)!.trigger('click'); await flushPromises() }
describe('persisted purchase return workspace', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
    vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
    api.getList.mockResolvedValue({ code: 10000, data: { rows: [{ id: 'source', number: '原采购单' }], total: 1 } })
    api.getDocument.mockResolvedValue({ code: 10000, data: { version: sourceVersion, header: { supplierName: '供应商' } } })
    api.preview.mockResolvedValue({ source: 'source', sourceVersion, sourceNumber: '原采购单', supplier: 'supplier', items: [item] })
    api.list.mockResolvedValue({ rows: [], total: 0 })
    api.document.mockResolvedValue({ version, sourceVersion, header: { id, source: 'source', number: '采购退货', supplierName: '供应商', timeText: '2026-11-16 00:00:00', money: 0, cost: 0, examine: 0, check: 0, nucleus: 0 }, items: [item] })
    api.sourceOptions.mockResolvedValue({ version, sourceVersion, items: [item] })
    api.accounts.mockResolvedValue([]); api.save.mockResolvedValue(id)
  })
  it('saves original line identity then reopens actual persisted UUID and binds refresh URL', async () => {
    const { wrapper, router } = await render()
    try {
      await click(wrapper, '选择此来源'); await click(wrapper, '保存退货草稿')
      expect(api.save).toHaveBeenCalledWith(expect.objectContaining({ source: 'source', sourceVersion, details: [expect.objectContaining({ source: 'original', nums: 2 })] }))
      const savedTime = new Date(api.save.mock.calls[0][0].time.replace(' ', 'T') + '+08:00').getTime()
      expect(Math.abs(savedTime - Date.now())).toBeLessThan(5000)
      expect(api.document).toHaveBeenCalledWith(id); expect(router.currentRoute.value.query.draft).toBe(id)
      expect(wrapper.text()).toContain('供应商')
    } finally { wrapper.unmount() }
  })
  it('reopens a saved draft without creating another and edits the exact displayed versions', async () => {
    const { wrapper } = await render('?draft=' + id)
    try { expect(api.preview).not.toHaveBeenCalled(); await click(wrapper, '保存草稿修改'); expect(api.save).toHaveBeenCalledWith(expect.objectContaining({ id, version, sourceVersion, details: [expect.objectContaining({ id: 'line', source: 'original', nums: 1 })] })) } finally { wrapper.unmount() }
  })
  it('keeps rejected input visible without fetching a new version for retry', async () => {
    api.save.mockRejectedValueOnce(new Error('来源数量已被占用'))
    const { wrapper } = await render('?draft=' + id)
    try { await wrapper.find('input[aria-label="退货单编号"]').setValue('保留输入'); await click(wrapper, '保存草稿修改'); expect(wrapper.text()).toContain('来源数量已被占用'); expect(wrapper.find('input[aria-label="退货单编号"]').element).toHaveProperty('value', '保留输入'); expect(api.document).toHaveBeenCalledTimes(1) } finally { wrapper.unmount() }
  })
  it('rejects stale source options before allowing edits to save', async () => {
    api.sourceOptions.mockResolvedValueOnce({ version: 'd'.repeat(64), sourceVersion, items: [item] })
    const { wrapper } = await render('?draft=' + id)
    try { expect(wrapper.text()).toContain('退货单或来源已变化'); await click(wrapper, '保存草稿修改'); expect(api.save).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('checks the displayed version without saving or silently refreshing before mutation', async () => {
    api.review.mockResolvedValueOnce(1)
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    const { wrapper } = await render('?draft=' + id)
    try { await click(wrapper, '核对退货单'); expect(api.review).toHaveBeenCalledWith([id], 1, version); expect(api.save).not.toHaveBeenCalled(); expect(api.document).toHaveBeenCalledTimes(2) } finally { wrapper.unmount() }
  })
  it('refuses unsaved edits instead of checking different content', async () => {
    const confirm = vi.spyOn(ElMessageBox, 'confirm')
    const { wrapper } = await render('?draft=' + id)
    try { await wrapper.find('input[aria-label="退货单编号"]').setValue('新内容'); await click(wrapper, '核对退货单'); expect(wrapper.text()).toContain('请先保存未提交的修改'); expect(api.review).not.toHaveBeenCalled(); expect(confirm).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('posts the displayed checked version and rereads only after successful mutation', async () => {
    const doc = await api.document(); doc.header.check = 1; api.document.mockResolvedValue(doc)
    api.post.mockResolvedValueOnce(1)
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    const { wrapper } = await render('?draft=' + id)
    try { await click(wrapper, '审核并入账'); expect(api.post).toHaveBeenCalledWith([id], 1, version); expect(api.save).not.toHaveBeenCalled(); expect(api.document).toHaveBeenCalledTimes(3) } finally { wrapper.unmount() }
  })
  it('keeps rejected posting visible without silently fetching a newer version', async () => {
    const doc = await api.document(); doc.header.check = 1; api.document.mockResolvedValue(doc)
    api.post.mockRejectedValueOnce(new Error('原仓库库存不足'))
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    const { wrapper } = await render('?draft=' + id)
    try { await click(wrapper, '审核并入账'); expect(wrapper.text()).toContain('原仓库库存不足'); expect(api.post).toHaveBeenCalledWith([id], 1, version); expect(api.document).toHaveBeenCalledTimes(2); expect(api.save).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
})
