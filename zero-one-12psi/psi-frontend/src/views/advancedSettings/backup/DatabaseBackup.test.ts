import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
const api = vi.hoisted(() => ({ getBackupStatus: vi.fn(), downloadDatabaseBackup: vi.fn() }))
vi.mock('@/apis/systemBackup', () => api)
import DatabaseBackup from './DatabaseBackup.vue'

describe('database backup interactions', () => {
  beforeEach(() => { api.getBackupStatus.mockReset(); api.downloadDatabaseBackup.mockReset() })
  const ready = { code: 10000, data: { database: 'qa_example', tables: 12, format: 'SQL', scope: '数据库结构和数据' } }
  function render() { return mount(DatabaseBackup, { global: { plugins: [ElementPlus] } }) }
  it('explains failed environment checks and supports an actual retry', async () => {
    api.getBackupStatus.mockRejectedValueOnce(new Error('Docker尚未启动')).mockResolvedValueOnce(ready)
    const wrapper = render()
    try {
      await flushPromises()
      expect(wrapper.text()).toContain('Docker尚未启动')
      expect(wrapper.findAll('button')[0].attributes('disabled')).toBeDefined()
      await wrapper.findAll('button')[1].trigger('click'); await flushPromises()
      expect(wrapper.text()).toContain('qa_example')
      expect(wrapper.text()).not.toContain('Docker尚未启动')
      expect(wrapper.findAll('button')[0].attributes('disabled')).toBeUndefined()
    } finally { wrapper.unmount() }
  })
  it('does not claim a successful backup or lose retry after download fails', async () => {
    api.getBackupStatus.mockResolvedValue(ready)
    api.downloadDatabaseBackup.mockRejectedValue(new Error('生成备份失败'))
    const wrapper = render()
    try {
      await flushPromises(); await wrapper.findAll('button')[0].trigger('click'); await flushPromises()
      expect(wrapper.text()).toContain('生成备份失败')
      expect(wrapper.text()).not.toContain('下载已发起')
      expect(wrapper.findAll('button')[0].attributes('disabled')).toBeUndefined()
    } finally { wrapper.unmount() }
  })
})
