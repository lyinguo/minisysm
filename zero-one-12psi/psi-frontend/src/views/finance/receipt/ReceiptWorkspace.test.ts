import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus, { ElMessageBox } from 'element-plus'
const api = vi.hoisted(() => ({ list: vi.fn(), document: vi.fn(), options: vi.fn(), save: vi.fn(), preview: vi.fn(), settle: vi.fn(), remove: vi.fn(), export: vi.fn() }))
vi.mock('@/apis/finance/receiptWorkflow', () => ({ receiptWorkflow: api }))
import Workspace from './ReceiptWorkspace.vue'
const id = 'receipt-id', version = 'a'.repeat(64)
const persisted = () => ({ version, header: { id, number: 'PAY001', customer: 'customer', customerName: '客户', timeText: '2026-11-16 14:00:00', data: '', total: 954, examine: 0, nucleus: 0 }, items: [{ id: 'line', pid: id, account: 'account', accountName: '银行账户', accountNumber: 'A001', money: 954, settle: '', data: '' }], allocations: [], expenses: [], invoices: [] })
async function render(initial = id) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/receipt-order-report', name: 'ReceiptOrderReport', component: Workspace }] })
  await router.push('/receipt-order-report?receipt=' + initial)
  const wrapper = mount({ template: '<router-view />' }, { global: { plugins: [router, ElementPlus], stubs: { ReceiptImportDialog: true, ElDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /><slot name="footer" /></div>' } } } })
  await flushPromises();return { wrapper, router }
}
async function click(wrapper: Awaited<ReturnType<typeof render>>['wrapper'], text: string) { await wrapper.findAll('button').find(button => button.text() === text)!.trigger('click');await flushPromises() }
describe('收款单明确业务流', () => {
  beforeEach(() => {
    vi.clearAllMocks();vi.restoreAllMocks()
    vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
    api.list.mockResolvedValue({ rows: [], total: 0 });api.document.mockResolvedValue(persisted());api.options.mockResolvedValue({ rows: [], hasMore: false });api.save.mockResolvedValue(id);api.settle.mockResolvedValue(1)
    const documents = [{ id: 'sell', type: 'sell', number: 'BUY001', version: 'b'.repeat(64), remaining: 1130, money: 1130 }, { id: 'return', type: 'sre', number: 'RET001', version: 'c'.repeat(64), remaining: 176, money: -176 }]
    api.preview.mockResolvedValue({ receipt: id, version, cash: 954, invoiceTotal: 1130, creditTotal: 176, receivableNet: 954, allocations: documents, documents })
  })
  it('刷新按实际ID重开，不新增；保存稳定明细ID及已读版本', async () => {
    const { wrapper } = await render()
    try { expect(api.document).toHaveBeenCalledWith(id);await click(wrapper, '保存草稿修改');expect(api.save).toHaveBeenCalledWith(id, expect.objectContaining({ version, details: [expect.objectContaining({ id: 'line', pid: id, account: 'account', amount: 954, data: '' })] }));expect(api.save.mock.calls[0][1].details[0]).not.toHaveProperty('money');expect(api.settle).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('未保存输入不能静默核对或收款', async () => {
    const { wrapper } = await render()
    try { await wrapper.find('input[aria-label="收款备注"]').setValue('未保存');await click(wrapper, '核对结算方案');expect(wrapper.text()).toContain('请先保存未提交的修改');expect(api.preview).not.toHaveBeenCalled();expect(api.settle).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('明确展示销售1130减退货176，确认后按原单冻结版本入账', async () => {
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    const { wrapper } = await render()
    try { await click(wrapper, '核对结算方案');expect(wrapper.text()).toContain('1130');expect(wrapper.text()).toContain('176');expect(api.settle).not.toHaveBeenCalled();await click(wrapper, '确认收款并核销');expect(api.settle).toHaveBeenCalledWith(id, 1, version, [expect.objectContaining({ id: 'sell', money: 1130, version: 'b'.repeat(64) }), expect.objectContaining({ id: 'return', money: -176, version: 'c'.repeat(64) })]) } finally { wrapper.unmount() }
  })
  it('过期收款版本不能用新预览静默覆盖并提交', async () => {
    const plan = await api.preview();plan.version = 'd'.repeat(64);api.preview.mockResolvedValue(plan)
    const { wrapper } = await render()
    try { await click(wrapper, '核对结算方案');expect(wrapper.text()).toContain('收款单已变化');expect(wrapper.text()).not.toContain('确认收款并核销');expect(api.document).toHaveBeenCalledOnce();expect(api.settle).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('实际审核失败保留原输入与方案，不显示成功或刷新成另一版本', async () => {
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    api.settle.mockRejectedValue(new Error('账户余额不足'))
    const { wrapper } = await render()
    try { await click(wrapper, '核对结算方案');await click(wrapper, '确认收款并核销');expect(wrapper.text()).toContain('账户余额不足');expect(wrapper.text()).toContain('确认收款并核销');expect(api.document).toHaveBeenCalledOnce() } finally { wrapper.unmount() }
  })
  it('已收款单只允许显式反审核，发送目标0而非切换或自动重付', async () => {
    const value = persisted();value.header.examine = 1;value.header.nucleus = 2;api.document.mockResolvedValue(value)
    vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>)
    const { wrapper } = await render()
    try { expect(wrapper.text()).not.toContain('保存草稿修改');await click(wrapper, '反审核并撤销本次收款');expect(api.settle).toHaveBeenCalledWith(id, 0, version, undefined);expect(api.save).not.toHaveBeenCalled() } finally { wrapper.unmount() }
  })
  it('同一页面切换收款ID会实际重读对应单据，不停留旧内容', async () => {
    const { wrapper, router } = await render()
    try {
      const next = persisted();next.header.id = 'next-receipt';next.header.number = 'NEXT001';api.document.mockResolvedValue(next)
      await router.push('/receipt-order-report?receipt=next-receipt');await flushPromises()
      expect(api.document).toHaveBeenLastCalledWith('next-receipt')
      expect(wrapper.find('input[aria-label="收款单编号"]').element).toHaveProperty('value', 'NEXT001')
    } finally { wrapper.unmount() }
  })
  it('拒绝放弃未保存输入时，真正阻止路由变化并保留输入', async () => {
    vi.spyOn(ElMessageBox, 'confirm').mockRejectedValue('cancel')
    const { wrapper, router } = await render()
    try {
      await wrapper.find('input[aria-label="收款备注"]').setValue('保留输入')
      await router.push('/receipt-order-report?receipt=next-receipt');await flushPromises()
      expect(router.currentRoute.value.query.receipt).toBe(id);expect(api.document).toHaveBeenCalledOnce()
      expect(wrapper.find('input[aria-label="收款备注"]').element).toHaveProperty('value', '保留输入')
    } finally { wrapper.unmount() }
  })
  it('列表打开另一张单同步真实URL，关闭清除详情参数，刷新按新ID读取', async () => {
    api.list.mockResolvedValue({ rows: [{ id: 'selected-receipt', number: 'SELECTED001', customerName: '客户', total: 25, examine: 0 }], total: 1 })
    const { wrapper, router } = await render()
    const next = persisted();next.header.id = 'selected-receipt';next.header.number = 'SELECTED001';api.document.mockResolvedValue(next)
    try {
      await click(wrapper, '关闭');expect(router.currentRoute.value.query.receipt).toBeUndefined()
      await click(wrapper, '查看 / 处理');expect(router.currentRoute.value.query.receipt).toBe('selected-receipt')
      expect(wrapper.find('input[aria-label="收款单编号"]').element).toHaveProperty('value', 'SELECTED001')
    } finally { wrapper.unmount() }
    const refreshed = await render('selected-receipt')
    try { expect(api.document).toHaveBeenLastCalledWith('selected-receipt');expect(refreshed.wrapper.find('input[aria-label="收款单编号"]').element).toHaveProperty('value', 'SELECTED001');expect(api.save).not.toHaveBeenCalled() } finally { refreshed.wrapper.unmount() }
  })
})
