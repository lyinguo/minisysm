import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'
import Report from './WarehouseDocumentReport.vue'

const mocks = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn(), post: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => mocks }))
const detail = () => ({
  version: 'v1',
  header: {
    id: 'd1',
    number: 'IN001',
    time: '2026-11-14 10:00:00',
    examine: 0,
    check: 0,
    data: ''
  },
  items: [{ id: 'i1', goods: 'g1', nums: 2, price: 5, warehouse: 'w1', data: '' }],
  goods: [{ id: 'g1', name: '测试商品', serial: 0 }]
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal(
    'ResizeObserver',
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
  )
  vi.spyOn(ElMessageBox, 'confirm').mockImplementation(vi.fn().mockResolvedValue('confirm'))
  mocks.get.mockImplementation(async (url: string) => ({
    code: 10000,
    data: url.includes('getWarehouseNameList')
      ? [{ id: 'w1', name: '测试仓库' }]
      : url.endsWith('/d1')
        ? detail()
        : { rows: [{ id: 'd1', number: 'IN001', examine: 0 }], total: 1 }
  }))
  mocks.put.mockImplementation(async () => ({ code: 10000, data: { ...detail(), version: 'v2' } }))
  mocks.post.mockImplementation(async (_url: string, body: { target: number }) => ({
    code: 10000,
    data: {
      ...detail(),
      version: 'v3',
      header: { ...detail().header, examine: body.target }
    }
  }))
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

async function open() {
  const wrapper = mount(Report, {
    props: { kind: 'entry', title: '入库单报表' },
    attachTo: document.body,
    global: { plugins: [ElementPlus] }
  })
  await flushPromises()
  const button = wrapper.findAll('button').find((b) => b.text().includes('详情 / 编辑'))!
  await button.trigger('click')
  await flushPromises()
  return wrapper
}

describe('warehouse document actions', () => {
  it('persists a real document without auditing on Save', async () => {
    const wrapper = await open()
    try {
      await wrapper
        .findAll('button')
        .find((b) => b.text() === '保存')!
        .trigger('click')
      await flushPromises()
      expect(mocks.put).toHaveBeenCalledWith(
        '/transfer/report-documents/entry/d1',
        expect.objectContaining({ version: 'v1' })
      )
      expect(mocks.post).not.toHaveBeenCalled()
    } finally {
      wrapper.unmount()
    }
  })
  it('saves before auditing and passes the latest document version', async () => {
    const wrapper = await open()
    try {
      const inputs = document.querySelectorAll('.el-dialog .el-input__inner')
      const number = inputs[0] as HTMLInputElement
      number.value = 'IN002'
      number.dispatchEvent(new Event('input', { bubbles: true }))
      await flushPromises()
      await wrapper
        .findAll('button')
        .find((b) => b.text() === '保存并审核')!
        .trigger('click')
      await flushPromises()
      expect(mocks.put).toHaveBeenCalledOnce()
      expect(mocks.post).toHaveBeenCalledWith('/transfer/report-documents/entry/d1/audit', {
        target: 1,
        version: 'v2'
      })
      expect(wrapper.findAll('button').some((b) => b.text() === '反审核')).toBe(true)
    } finally {
      wrapper.unmount()
    }
  })
  it('does not audit if persisting edits fails', async () => {
    mocks.put.mockRejectedValueOnce(new Error('单据已被其他操作修改'))
    const wrapper = await open()
    try {
      const number = document.querySelector('.el-dialog .el-input__inner') as HTMLInputElement
      number.value = 'IN002'
      number.dispatchEvent(new Event('input', { bubbles: true }))
      await flushPromises()
      await wrapper
        .findAll('button')
        .find((b) => b.text() === '保存并审核')!
        .trigger('click')
      await flushPromises()
      expect(mocks.post).not.toHaveBeenCalled()
      expect(wrapper.findAll('button').some((b) => b.text() === '保存并审核')).toBe(true)
    } finally {
      wrapper.unmount()
    }
  })
  it('audits an unchanged checked document without an implicit edit permission', async () => {
    mocks.get.mockImplementation(async (url: string) => ({
      code: 10000,
      data: url.endsWith('/d1')
        ? { ...detail(), header: { ...detail().header, check: 1 } }
        : url.includes('getWarehouseNameList')
          ? []
          : { rows: [{ id: 'd1', number: 'IN001' }], total: 1 }
    }))
    const wrapper = await open()
    try {
      expect(wrapper.findAll('button').some((b) => b.text() === '保存')).toBe(false)
      await wrapper
        .findAll('button')
        .find((b) => b.text() === '保存并审核')!
        .trigger('click')
      await flushPromises()
      expect(mocks.put).not.toHaveBeenCalled()
      expect(mocks.post).toHaveBeenCalledWith('/transfer/report-documents/entry/d1/audit', {
        target: 1,
        version: 'v1'
      })
    } finally {
      wrapper.unmount()
    }
  })
})
