import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  interceptors: {} as any,
  store: {
    getToken: 'old-token' as string | null,
    reloadToken: vi.fn(),
    clearSession: vi.fn()
  },
  replace: vi.fn(),
  warning: vi.fn(),
  retry: vi.fn()
}))

vi.mock('@/stores/user', () => ({ useUserStore: () => mocks.store }))
vi.mock('element-plus', () => ({ ElMessage: { warning: mocks.warning, error: vi.fn() } }))
vi.mock('@/apis/http', () => ({
  default: class {
    constructor(_: unknown, interceptors: unknown) { mocks.interceptors = interceptors }
    getInstance() { return { request: mocks.retry } }
  },
  closeLoading: vi.fn(), showLoading: vi.fn(), DataUpType: {}
}))

import plugin from './http'

describe('expired login handling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.store.getToken = 'old-token'
    mocks.store.clearSession.mockImplementation(() => { mocks.store.getToken = null })
    mocks.replace.mockImplementation(() => {
      expect(mocks.store.getToken).toBeNull()
      return Promise.resolve()
    })
    plugin.install({ provide: vi.fn() } as any, { router: { replace: mocks.replace } as any })
  })

  it('clears credentials before redirecting when refresh returns a business failure', async () => {
    await expect(mocks.interceptors.responseInterceptor({
      config: { url: '/login/refresh-token' },
      data: { code: 9999, data: 'Invalid refresh token (expired)' }
    })).rejects.toThrow('登录已过期')
    expect(mocks.store.clearSession).toHaveBeenCalledOnce()
    expect(mocks.replace).toHaveBeenCalledWith('/login')
    expect(mocks.store.reloadToken).not.toHaveBeenCalled()
  })

  it('handles HTTP refresh rejection without recursively refreshing', async () => {
    await expect(mocks.interceptors.responseErrorInterceptor({
      config: { url: '/login/refresh-token' }, response: { status: 400 }
    })).rejects.toThrow('登录已过期')
    expect(mocks.replace).toHaveBeenCalledOnce()
    expect(mocks.store.reloadToken).not.toHaveBeenCalled()
  })

  it('redirects when automatic refresh fails', async () => {
    mocks.store.reloadToken.mockRejectedValueOnce(new Error('expired'))
    await expect(mocks.interceptors.responseInterceptor({
      config: { url: '/user' }, data: { code: 401, data: 'Jwt expired at yesterday' }
    })).rejects.toThrow('登录已过期')
    expect(mocks.replace).toHaveBeenCalledWith('/login')
  })

  it('shares one refresh and retries each original request', async () => {
    let resolveRefresh!: () => void
    mocks.store.reloadToken.mockReturnValueOnce(new Promise<void>(resolve => { resolveRefresh = resolve }))
    mocks.retry.mockResolvedValue({ data: { code: 10000 } })
    const response = () => ({ config: { url: '/user' }, data: { code: 401, data: 'Jwt expired at yesterday' } })
    const requests = [mocks.interceptors.responseInterceptor(response()), mocks.interceptors.responseInterceptor(response())]
    resolveRefresh()
    await Promise.all(requests)
    expect(mocks.store.reloadToken).toHaveBeenCalledOnce()
    expect(mocks.retry).toHaveBeenCalledTimes(2)
    expect(mocks.replace).not.toHaveBeenCalled()
  })

  it('does not refresh a retried request again', async () => {
    await expect(mocks.interceptors.responseInterceptor({
      config: { url: '/user', _authRetried: true }, data: { code: 401, data: 'Jwt expired at yesterday' }
    })).rejects.toThrow('登录已过期')
    expect(mocks.store.reloadToken).not.toHaveBeenCalled()
    expect(mocks.replace).toHaveBeenCalledOnce()
  })
})
