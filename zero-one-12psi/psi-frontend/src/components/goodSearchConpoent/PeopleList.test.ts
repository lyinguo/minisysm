import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElTable } from 'element-plus'
const api = vi.hoisted(() => ({ getPersonnelList: vi.fn() }))
vi.mock('@/apis/advancedSettings/people', () => api)
vi.mock('./GoodSearchForm.vue', () => ({ default: { name: 'GoodSearchForm', template: '<div />' } }))
import PeopleList from './PeopleList.vue'
describe('real personnel selection', () => {
  beforeEach(() => { api.getPersonnelList.mockReset() })
  it('queries real records without emitting selection until a returned row is chosen', async () => {
    api.getPersonnelList.mockResolvedValue({ code: 10000, data: { rows: [{ id: 'person-uuid', name: '实际人员', number: 'P001', frame: 'qa', sex: 0 }], total: 1 } })
    const wrapper = mount(PeopleList, { global: { plugins: [ElementPlus] } })
    try {
      await flushPromises()
      expect(wrapper.emitted('search')).toBeUndefined()
      wrapper.findComponent({ name: 'GoodSearchForm' }).vm.$emit('search', { peopleName: '实际人员' }); await flushPromises()
      expect(api.getPersonnelList).toHaveBeenLastCalledWith(expect.objectContaining({ pageIndex: 1, pageSize: 20, name: '实际人员' }))
      expect(wrapper.emitted('search')).toBeUndefined()
      const table = wrapper.findComponent(ElTable)
      const rows = table.props('data') || []
      expect(rows).toHaveLength(1)
      table.vm.$emit('row-click', rows[0]); await flushPromises()
      expect(wrapper.emitted('search')?.[0]?.[0]).toEqual(expect.objectContaining({ id: 'person-uuid', name: '实际人员', number: 'P001' }))
    } finally { wrapper.unmount() }
  })
  it('keeps service failure visible without mock rows or a false selected person', async () => {
    api.getPersonnelList.mockRejectedValue(new Error('人员服务不可用'))
    const wrapper = mount(PeopleList, { global: { plugins: [ElementPlus] } })
    try { await flushPromises(); expect(wrapper.text()).toContain('人员服务不可用'); expect(wrapper.findComponent(ElTable).exists()).toBe(false); expect(wrapper.emitted('search')).toBeUndefined() }
    finally { wrapper.unmount() }
  })
})
