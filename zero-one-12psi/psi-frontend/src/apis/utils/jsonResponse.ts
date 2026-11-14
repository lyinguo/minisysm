import type { RequestCallback } from '@/plugins/http'

const SUCCESS_CODE = 10000

/** 从 http 插件返回的 JsonVO 或异常中提取可读错误信息 */
export function extractErrorMessage(err: unknown): string {
  if (err instanceof Error && err.message) {
    return err.message
  }
  const anyErr = err as any
  const body = anyErr?.response?.data ?? anyErr?.data ?? anyErr
  if (body && typeof body === 'object') {
    if (typeof body.data === 'string' && body.data) {
      return body.data
    }
    if (typeof body.data?.message === 'string' && body.data.message) return body.data.message
    if (typeof body.message === 'string' && body.message) {
      return body.message
    }
  }
  return '请求失败'
}

/**
 * 统一处理 JsonVO 响应：仅 code=10000 走 success，否则 fail 并带上后端 message
 */
export async function handleJsonRequest<T>(
  request: Promise<{ code?: number; message?: string; data?: T }>,
  success: RequestCallback,
  fail: RequestCallback
) {
  try {
    const body = await request
    if (body?.code === SUCCESS_CODE) {
      success(body.data)
      return
    }
    fail(new Error(body?.message || extractErrorMessage(body)))
  } catch (err) {
    fail(new Error(extractErrorMessage(err)))
  }
}
