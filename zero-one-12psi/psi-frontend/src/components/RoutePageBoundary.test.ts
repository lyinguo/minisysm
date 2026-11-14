import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, shallowRef } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import Boundary from './RoutePageBoundary.vue'

describe('route render failures', () => {
  it('shows recovery controls and lets another route render', async () => {
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    const path = shallowRef('broken')
    const Broken = defineComponent({
      setup() {
        throw new Error('broken page')
      }
    })
    const wrapper = mount(
      defineComponent({
        setup: () => () =>
          h(
            Boundary,
            { key: path.value },
            {
              default: () => (path.value === 'broken' ? h(Broken) : h('div', '正常页面'))
            }
          )
      }),
      { global: { plugins: [ElementPlus] } }
    )
    try {
      await flushPromises()
      expect(wrapper.text()).toContain('页面加载失败')
      path.value = 'working'
      await flushPromises()
      expect(wrapper.text()).toBe('正常页面')
    } finally {
      wrapper.unmount()
      log.mockRestore()
    }
  })
})
