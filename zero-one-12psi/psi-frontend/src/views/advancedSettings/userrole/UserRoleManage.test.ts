import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus, { ElMessage } from 'element-plus'
const api = vi.hoisted(() => ({
  getRoleList: vi.fn(), getRoleDetail: vi.fn(), getRolePermission: vi.fn(),
  addRole: vi.fn(), modifyRole: vi.fn(), deleteRole: vi.fn()
}))
vi.mock('@/apis/advancedSettings/userrole', () => api)
vi.mock('@/apis/advancedSettings/organization', () => ({ getOrganizationTree: vi.fn(async () => ({ code: 10000, data: [] })) }))
import UserRoleManage from './UserRoleManage.vue'

describe('role save', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    vi.clearAllMocks()
    api.getRoleList.mockResolvedValue({ code: 10000, data: { rows: [], total: 0 } })
    api.getRolePermission.mockResolvedValue({ code: 10000, data: { functionPermissions: [{ id: 'menu', name: '菜单' }] } })
    api.getRoleDetail.mockResolvedValue({ code: 10000, data: {
      id: 'role', name: '角色', data: '旧备注', root: '{"legacy-permission":true}', auth: '{"customer":"custom","extra":true}'
    } })
    api.modifyRole.mockResolvedValue({ code: 10000 })
  })
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

  async function open() {
    const wrapper = mount(UserRoleManage, { global: { plugins: [ElementPlus] } })
    await flushPromises()
    const state = (wrapper.vm as any).$.setupState
    await state.handleDetail({ id: 'role' })
    await flushPromises()
    await vi.runAllTimersAsync()
    return { wrapper, state }
  }

  it.each(['新备注', ''])('submits the current remark (%s) and preserves untouched permissions', async remark => {
    const { wrapper, state } = await open()
    try {
      state.formData.remark = remark
      await state.handleSave()
      expect(api.modifyRole).toHaveBeenCalledWith(expect.objectContaining({
        data: remark, root: '{"legacy-permission":true}', auth: '{"customer":"custom","extra":true}'
      }))
      expect(state.dialogVisible).toBe(false)
    } finally { wrapper.unmount() }
  })

  it('keeps the dialog open and displays the actual error on failure', async () => {
    const { wrapper, state } = await open()
    const error = vi.spyOn(ElMessage, 'error')
    try {
      api.modifyRole.mockRejectedValueOnce(new Error('角色已不存在，请刷新'))
      await state.handleSave()
      expect(error).toHaveBeenCalledWith('角色已不存在，请刷新')
      expect(state.dialogVisible).toBe(true)
      expect(state.saving).toBe(false)
    } finally { wrapper.unmount() }
  })

  it('saves permissions when the user explicitly changes the permission controls', async () => {
    const { wrapper, state } = await open()
    try {
      state.treeRef.setCheckedKeys(['menu'])
      wrapper.findAllComponents({ name: 'ElTree' })[0].vm.$emit('check', {})
      const select = wrapper.findAllComponents({ name: 'ElSelect' }).find(select => select.props('modelValue') === 'custom')!
      select.vm.$emit('update:modelValue', 'org')
      select.vm.$emit('change', 'org')
      await flushPromises()
      await state.handleSave()
      const payload = api.modifyRole.mock.calls[0][0]
      expect(JSON.parse(payload.root)).toEqual({ menu: true })
      expect(JSON.parse(payload.auth)).toMatchObject({ customer: 'org', extra: true })
    } finally { wrapper.unmount() }
  })

  it('does not send duplicate saves while a request is running', async () => {
    const { wrapper, state } = await open()
    try {
      let resolve!: (value: unknown) => void
      api.modifyRole.mockImplementationOnce(() => new Promise(done => { resolve = done }))
      const pending = state.handleSave()
      await state.handleSave()
      expect(api.modifyRole).toHaveBeenCalledTimes(1)
      resolve({ code: 10000 })
      await pending
    } finally { wrapper.unmount() }
  })

  it('does not dereference a destroyed permission tree after a fast save', async () => {
    const wrapper = mount(UserRoleManage, { global: { plugins: [ElementPlus] } })
    try {
      await flushPromises()
      const state = (wrapper.vm as any).$.setupState
      await state.handleDetail({ id: 'role' })
      await flushPromises()
      await state.handleSave()
      await flushPromises()
      await vi.runAllTimersAsync()
      expect(state.dialogVisible).toBe(false)
    } finally { wrapper.unmount() }
  })
})
