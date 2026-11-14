import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus, { ElMessageBox } from 'element-plus'
const http = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => http }))
import SystemSettings from './SystemSettings.vue'

describe('unsupported system rules', () => {
  it('keeps rule controls read-only and excludes them when saving other settings', async () => {
    http.get.mockResolvedValue({ code: 10000, data: [{ id: 'fun', name: 'fun', info: '{"examine":true,"valuation":"ma"}' }] })
    http.put.mockResolvedValue({ code: 10000 })
    const confirm = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue(
      'confirm' as Awaited<ReturnType<typeof ElMessageBox.confirm>>
    )
    const wrapper = mount(SystemSettings, { global: { plugins: [ElementPlus] } })
    try {
      await flushPromises()
      const state = (wrapper.vm as any).$.setupState
      state.currentTab = 'function'
      await flushPromises()
      expect(wrapper.text()).toContain('功能参数暂只读')
      expect(wrapper.find('.el-switch.is-disabled').exists()).toBe(true)
      state.handleSave()
      await flushPromises()
      expect(http.put).toHaveBeenCalled()
      const saved = http.put.mock.calls[0][1]
      expect(saved.some((item: { name: string }) => item.name === 'fun')).toBe(false)
    } finally { wrapper.unmount(); confirm.mockRestore() }
  })
})
