/*
 * @Description: 系统配置-导入模板相关接口
 */
import { useHttp, type RequestCallback } from '@/plugins/http'
import { DataUpType } from '@/apis/http'
import type { PageDTO } from '@/components/mytable/type'
import { handleJsonRequest } from '@/apis/utils/jsonResponse'
import type {
  PageRequest,
  ImportTemplateList,
  ImportTemplateDetail
} from './type'

const currBaseUrl = '/j1-sysc/import-template'
const http = useHttp()

export const getTemplateList = async (
  params: PageRequest,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.get<PageDTO<ImportTemplateList>>(`${currBaseUrl}/list`, params, { showLoading: true }),
    success,
    fail
  )
}

export const getTemplateDetail = async (
  id: string,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.get<ImportTemplateDetail>(`${currBaseUrl}/download/${id}`, {}, { showLoading: true }),
    (data: ImportTemplateDetail) => {
      if (data?.id) {
        // 统一走网关代理下载，避免 FastDFS 外链不可访问
        data.downloadUrl = `/api/j1-sysc/import-template/file/${data.id}`
      }
      success(data)
    },
    fail
  )
}

export const importTemplate = async (
  formData: FormData,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.post<string>(`${currBaseUrl}/import`, formData, {
      showLoading: true,
      upType: DataUpType.file
    }),
    success,
    fail
  )
}

export const updateTemplate = async (
  id: string,
  formData: FormData,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.put<string>(`${currBaseUrl}/update/${id}`, formData, {
      showLoading: true,
      upType: DataUpType.file
    }),
    success,
    fail
  )
}

export const deleteTemplate = async (
  id: string,
  success: RequestCallback,
  fail: RequestCallback
) => {
  return handleJsonRequest(
    http.delete<string>(`${currBaseUrl}/delete/${id}`, {}, { showLoading: true }),
    success,
    fail
  )
}

/** 带鉴权下载模板文件（避免浏览器直接打开导致无 Token / Whitelabel 500） */
export const downloadTemplateFile = async (id: string, fileName?: string): Promise<void> => {
  if (!id?.trim()) {
    throw new Error('模板ID不能为空')
  }

  const saveBlob = async (res: any) => {
    const data = res?.data ?? res
    if (!data) {
      throw new Error('下载失败：空响应')
    }
    const blob: Blob = data instanceof Blob ? data : new Blob([data])
    const contentType = (res?.headers?.['content-type'] || blob.type || '').toLowerCase()
    if (contentType.includes('application/json') || contentType.includes('text/')) {
      const text = await blob.text()
      try {
        const json = JSON.parse(text)
        throw new Error(json.message || (typeof json.data === 'string' ? json.data : '') || '下载失败')
      } catch (e) {
        if (e instanceof SyntaxError) {
          throw new Error(text || '下载失败')
        }
        throw e
      }
    }

    const disposition = res?.headers?.['content-disposition'] as string | undefined
    let name = fileName || 'template'
    if (disposition) {
      const matched = /filename\*?=(?:UTF-8'')?["']?([^"';]+)/i.exec(disposition)
      if (matched?.[1]) {
        name = decodeURIComponent(matched[1].replace(/\+/g, ' '))
      }
    }

    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = name
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  try {
    const res = await http.getFile(
      `${currBaseUrl}/file/${id.trim()}`,
      {},
      { responseType: 'blob', showLoading: true }
    )
    await saveBlob(res)
  } catch (error: any) {
    const errData = error?.response?.data
    if (errData instanceof Blob) {
      const text = await errData.text()
      try {
        const json = JSON.parse(text)
        throw new Error(json.message || '下载失败')
      } catch (e) {
        if (e instanceof SyntaxError) {
          throw new Error(text || '下载失败')
        }
        throw e
      }
    }
    if (error instanceof Error) {
      throw error
    }
    throw new Error('下载失败')
  }
}

