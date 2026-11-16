import { beforeEach, describe, expect, it, vi } from 'vitest'
const mocks = vi.hoisted(() => ({ post: vi.fn(), setToken: vi.fn(), setLoaded: vi.fn() }))
vi.mock('@/plugins/http', () => ({ useHttp: () => ({ post: mocks.post }), DataUpType: { form: 'form' } }))
vi.mock('@/stores/user', () => ({ useUserStore: () => mocks }))
import { login } from '@/apis/login'
const input = { username: 'unit-test-user', password: 'not-a-real-password' }
describe('login response and session handling', () => {
  beforeEach(() => vi.clearAllMocks())
  it('stores successful credentials and reloads account grants before success callback', async () => {
    const tokens = { token: 'test.access.token', refreshToken: 'test.refresh.token', tokenHead: 'Bearer' }
    const response = { code: 10000, data: tokens }; mocks.post.mockResolvedValue(response)
    const success = vi.fn(), fail = vi.fn(); await login(input, success, fail)
    expect(mocks.setToken).toHaveBeenCalledWith(tokens); expect(mocks.setLoaded).toHaveBeenCalledWith(false)
    expect(success).toHaveBeenCalledWith(response); expect(fail).not.toHaveBeenCalled()
  })
  it('does not accept credentials included in a rejected business response', async () => {
    const response = { code: 9995, data: { token: 'rejected.test.token' }, message: '登录失败' }
    mocks.post.mockResolvedValue(response); const success = vi.fn(), fail = vi.fn(); await login(input, success, fail)
    expect(mocks.setToken).not.toHaveBeenCalled(); expect(mocks.setLoaded).not.toHaveBeenCalled()
    expect(success).not.toHaveBeenCalled(); expect(fail).toHaveBeenCalledWith(response)
  })
  it('refuses successful-looking responses without a usable access token', async () => {
    for (const data of [null, {}, { token: '' }, { token: '   ' }]) {
      mocks.post.mockResolvedValue({ code: 10000, data }); const success = vi.fn(), fail = vi.fn()
      await login(input, success, fail); expect(success).not.toHaveBeenCalled(); expect(fail).toHaveBeenCalledTimes(1)
    }
    expect(mocks.setToken).not.toHaveBeenCalled()
  })
  it('reports transport failure without overwriting the existing session', async () => {
    const error = new Error('测试网络失败'); mocks.post.mockRejectedValue(error)
    const success = vi.fn(), fail = vi.fn(); await login(input, success, fail)
    expect(mocks.setToken).not.toHaveBeenCalled(); expect(success).not.toHaveBeenCalled(); expect(fail).toHaveBeenCalledWith(error)
  })
})
