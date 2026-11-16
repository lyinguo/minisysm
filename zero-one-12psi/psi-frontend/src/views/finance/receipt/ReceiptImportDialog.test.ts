import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'
const api = vi.hoisted(() => ({ template: vi.fn(), previewFile: vi.fn(), importFile: vi.fn() }))
vi.mock('@/apis/finance/receiptWorkflow', () => ({ receiptWorkflow: api }))
import ImportDialog from './ReceiptImportDialog.vue'
const version = 'c'.repeat(64)
const preview = () => ({ version, documents: [{ number: 'QA001', time: '2026-11-16 14:00:00', total: 25 }], references: [{ number: 'QA001', customerNumber: 'C001', customer: '实际客户', accountNumber: 'A001', account: '实际账户', money: 25 }], documentCount: 1, lineCount: 1, cash: 25 })
function render() { return mount(ImportDialog, { props: { modelValue: true }, global: { plugins: [ElementPlus], stubs: { ElDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /><slot name="footer" /></div>' } } } }) }
async function upload(wrapper: ReturnType<typeof render>, file = new File(['component fixture, parsed by server in production'], '收款.xlsx')) { Object.defineProperty(wrapper.find('input[type="file"]').element, 'files', { configurable: true, value: [file] });await wrapper.find('input[type="file"]').trigger('change');await flushPromises();return file }
async function confirm(wrapper: ReturnType<typeof render>) { await wrapper.findAll('button').find(button => button.text().includes('确认导入'))!.trigger('click');await flushPromises() }
describe('收款原文件核对与明确确认', () => {
  beforeEach(() => { vi.clearAllMocks();vi.restoreAllMocks();vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });api.previewFile.mockImplementation(async () => preview());api.importFile.mockResolvedValue({ ids: ['real-id'], documentCount: 1, lineCount: 1, cash: 25 });vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>) })
  it('先显示服务端实际业务名称，确认才提交同一原File对象和冻结版本', async () => {
    const wrapper = render()
    try { const file = await upload(wrapper);expect(api.previewFile).toHaveBeenCalledWith(file);expect(api.importFile).not.toHaveBeenCalled();expect(wrapper.text()).toContain('实际客户');expect(wrapper.text()).toContain('实际账户');expect(wrapper.text()).toContain('2026-11-16 14:00:00');await confirm(wrapper);expect(api.importFile).toHaveBeenCalledWith(file, version);expect(wrapper.emitted('saved')).toEqual([[['real-id']]]) } finally { wrapper.unmount() }
  })
  it('服务端预览拒绝后保留可理解原因，不能跳过核对提交', async () => {
    api.previewFile.mockRejectedValueOnce(new Error('客户编号不存在'))
    const wrapper = render()
    try { await upload(wrapper);expect(wrapper.text()).toContain('客户编号不存在');await confirm(wrapper);expect(api.importFile).not.toHaveBeenCalled();expect(wrapper.emitted('saved')).toBeUndefined() } finally { wrapper.unmount() }
  })
  it('结果未确认时阻止重复提交，提示先按单据编号查验', async () => {
    api.importFile.mockRejectedValueOnce(new Error('连接中断'))
    const wrapper = render()
    try { await upload(wrapper);await confirm(wrapper);expect(wrapper.text()).toContain('先按单据编号查询结果');await confirm(wrapper);expect(api.importFile).toHaveBeenCalledOnce();expect(wrapper.emitted('saved')).toBeUndefined() } finally { wrapper.unmount() }
  })
  it('确认等待期间选择了新文件，不能将旧核对版本用于新文件', async () => {
    let resolve!: (value: Awaited<ReturnType<typeof ElMessageBox.confirm>>) => void
    vi.spyOn(ElMessageBox, 'confirm').mockImplementationOnce(() => new Promise(done => { resolve = done }) as ReturnType<typeof ElMessageBox.confirm>)
    const wrapper = render()
    try { await upload(wrapper);await confirm(wrapper);await upload(wrapper, new File(['another component fixture'], '新收款.xlsx'));resolve('confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>);await flushPromises();expect(api.importFile).not.toHaveBeenCalled();expect(wrapper.text()).toContain('模板或预览已变化') } finally { wrapper.unmount() }
  })
})
