import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus, { ElSelect, ElMessageBox } from 'element-plus'
const mocks = vi.hoisted(() => ({ sourceList: vi.fn(), sourceDocument: vi.fn(), preview: vi.fn(), list: vi.fn(), document: vi.fn(), save: vi.fn(), remove: vi.fn(), accounts: vi.fn(), review: vi.fn() }))
vi.mock('@/apis/sales/order', () => ({ saleOrderApi: { getSaleList: mocks.sourceList, getDocument: mocks.sourceDocument, getGenerateReturnData: mocks.preview } }))
vi.mock('@/apis/sales/returnDraft', () => ({ returnDraftApi: mocks }))
import Workspace from './SalesReturnWorkspace.vue'
const source = 'a'.repeat(32), identifier = 'b'.repeat(32), sourceVersion = 'c'.repeat(64)
function document() { return { version: 'd'.repeat(64), sourceVersion, header: { id: identifier, source, sourceNumber: 'QA-SOURCE', customer: 'customer', customerName: 'QA customer', number: 'QA-RETURN', timeText: '2026-11-16 12:00:00', money: 0, cost: 0, examine: 0, check: 0, nucleus: 0, data: 'saved remark' }, items: [{ id: 'line-id', source: 'source-line', goodsName: 'QA goods', warehouseName: 'QA warehouse', unit: 'unit', nums: 1, price: 100, tpt: 113, serial: '[]' }] } }
async function render(query = '') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/sales-return', name: 'SalesReturn', component: { template: '<div />' } }] })
  await router.push('/sales-return' + query)
  const wrapper = mount(Workspace, { global: { plugins: [router, ElementPlus], stubs: { ElDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /><slot name="footer" /></div>' } } } })
  await flushPromises(); return wrapper
}
async function button(wrapper: Awaited<ReturnType<typeof render>>, label: string) { await wrapper.findAll('button').find(item => item.text() === label)!.trigger('click'); await flushPromises() }
describe('actual sales return draft workspace', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} unobserve() {} })
    mocks.sourceList.mockResolvedValue({ code: 10000, data: { total: 1, rows: [{ id: source, number: 'QA-SOURCE', customerName: 'QA customer', actual: 226 }] } })
    mocks.sourceDocument.mockResolvedValue({ code: 10000, data: { version: sourceVersion, header: { customerName: 'QA customer' } } })
    mocks.preview.mockResolvedValue({ code: 10000, data: { source, sourceVersion, sourceNumber: 'QA-SOURCE', customer: 'customer', items: [{ source: 'source-line', goodsName: 'QA goods', warehouseName: 'QA warehouse', unit: 'unit', available: 2, nums: 2, price: 100, tpt: 226 }] } })
    mocks.list.mockResolvedValue({ total: 0, rows: [] })
    mocks.document.mockResolvedValue(document())
    mocks.save.mockResolvedValue(identifier)
    mocks.accounts.mockResolvedValue([])
    mocks.review.mockResolvedValue(1)
  })
  it('reviews the displayed saved version and rereads only after successful mutation', async () => {
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    const wrapper = await render('?draft=' + identifier)
    try {
      await button(wrapper, '核对退货单')
      expect(mocks.review).toHaveBeenCalledWith([identifier], 1, 'd'.repeat(64))
      expect(mocks.document).toHaveBeenCalledTimes(2)
      expect(mocks.save).not.toHaveBeenCalled()
    } finally { wrapper.unmount() }
  })
  it('refuses to review unsaved edits without silently saving them', async () => {
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    const wrapper = await render('?draft=' + identifier)
    try {
      await wrapper.find('input[aria-label="退货单编号"]').setValue('CHANGED')
      await button(wrapper, '核对退货单')
      expect(wrapper.text()).toContain('请先保存未提交的修改')
      expect(confirm).not.toHaveBeenCalled()
      expect(mocks.review).not.toHaveBeenCalled()
      expect(mocks.save).not.toHaveBeenCalled()
    } finally { wrapper.unmount() }
  })
  it('keeps a rejected frozen review visible without automatically blessing a newer version', async () => {
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    mocks.review.mockRejectedValueOnce(new Error('退货版本已变化'))
    const wrapper = await render('?draft=' + identifier)
    try {
      await button(wrapper, '核对退货单')
      expect(wrapper.text()).toContain('退货版本已变化')
      expect(mocks.document).toHaveBeenCalledTimes(1)
      expect(mocks.save).not.toHaveBeenCalled()
    } finally { wrapper.unmount() }
  })
  it('submits selected source IDs and quantities, then actually rereads the persisted draft', async () => {
    const wrapper = await render()
    try {
      await button(wrapper, '选择此来源')
      await wrapper.find('input[aria-label="退货单编号"]').setValue('QA-RETURN')
      await wrapper.find('input[aria-label="退货数量 QA goods"]').setValue('1')
      await wrapper.find('input[aria-label="退货数量 QA goods"]').trigger('blur')
      expect((wrapper.find('input[aria-label="退货数量 QA goods"]').element as HTMLInputElement).value).toBe('1')
      expect(wrapper.text()).toContain('选中明细预计含税合计：113.0000')
      await button(wrapper, '保存退货草稿')
      expect(mocks.save).toHaveBeenCalledWith(expect.objectContaining({ source, sourceVersion, number: 'QA-RETURN', salesReturnOrderInfos: [{ id: undefined, source: 'source-line', nums: 1, serial: '[]', data: '' }] }))
      expect(mocks.document).toHaveBeenCalledWith(identifier)
      expect(wrapper.vm.$route.query).toEqual({ draft: identifier })
      expect(wrapper.text()).toContain('已保存')
      expect(wrapper.findAll('button').some(item => item.text() === '保存草稿修改')).toBe(true)
    } finally { wrapper.unmount() }
  })
  it('keeps a failed save visible and does not invent a saved ID or reread a new version', async () => {
    mocks.save.mockRejectedValue(new Error('可退数量已经被其他草稿占用'))
    const wrapper = await render()
    try { await button(wrapper, '选择此来源'); await button(wrapper, '保存退货草稿'); expect(wrapper.text()).toContain('可退数量已经被其他草稿占用'); expect(mocks.document).not.toHaveBeenCalled(); expect(wrapper.findAll('button').some(item => item.text() === '保存退货草稿')).toBe(true) } finally { wrapper.unmount() }
  })
  it('does not create again when saving succeeded but the persisted detail cannot be read', async () => {
    mocks.document.mockRejectedValue(new Error('详情读取暂不可用'))
    const wrapper = await render()
    try { await button(wrapper, '选择此来源'); await button(wrapper, '保存退货草稿'); expect(wrapper.text()).toContain('草稿已保存，详情读取失败'); const save = wrapper.findAll('button').find(item => item.text() === '保存草稿修改')!; expect(save.attributes('disabled')).toBeDefined(); await save.trigger('click'); expect(mocks.save).toHaveBeenCalledTimes(1); expect(wrapper.text()).toContain('重新读取草稿') } finally { wrapper.unmount() }
  })
  it('rejects a stale version transferred from the source preview instead of blessing it', async () => {
    const wrapper = await render('?source=' + source + '&sourceVersion=' + 'e'.repeat(64))
    try { expect(wrapper.text()).toContain('来源销售单已变化'); expect(wrapper.findAll('button').some(item => item.text() === '保存退货草稿')).toBe(false); expect(mocks.save).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('refuses zero selected quantities locally without silently dropping the selected line', async () => {
    const wrapper = await render()
    try { await button(wrapper, '选择此来源'); await wrapper.find('input[aria-label="退货数量 QA goods"]').setValue('0'); await button(wrapper, '保存退货草稿'); expect(wrapper.text()).toContain('数量大于零'); expect(mocks.save).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('reopens an actual saved draft URL without preparing another new source draft', async () => {
    const wrapper = await render('?draft=' + identifier)
    try { expect(mocks.document).toHaveBeenCalledWith(identifier); expect(mocks.preview).not.toHaveBeenCalled(); expect(mocks.sourceDocument).not.toHaveBeenCalled(); expect(wrapper.text()).toContain('已保存'); expect(mocks.save).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('does not let the initial account preload overwrite a later keyword search', async () => {
    let finish!:(rows:any[])=>void
    mocks.accounts.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve})).mockResolvedValue([{id:'chosen-account',name:'Filtered refund account',number:'UNIQUE'}])
    const wrapper=await render()
    try {await button(wrapper,'选择此来源');const search=wrapper.findComponent(ElSelect).props('remoteMethod') as (value:string)=>void;search('UNIQUE');await flushPromises();finish([{id:'old-account',name:'Old unfiltered account'}]);await flushPromises();expect(mocks.accounts).toHaveBeenLastCalledWith(source,'UNIQUE',false);expect(wrapper.findComponent(ElSelect).findAllComponents({name:'ElOption'}).map(option=>option.props('value'))).toEqual(['chosen-account'])}finally{wrapper.unmount()}
  })
})
