import { useHttp } from '@/plugins/http'
export async function uploadAvatar(file: File): Promise<{ id: string; url: string }> {
  const result = await useHttp().postWithFile<{ id: string; url: string }>('/j7-sysargs/attachment/avatar', { file })
  if (result.code !== 10000 || !result.data?.id) throw new Error(result.message || '头像上传失败')
  return result.data
}
export async function loadAvatar(id: string): Promise<string> {
  const response = await useHttp().getFile('/j7-sysargs/attachment/avatar/' + encodeURIComponent(id), undefined, { responseType: 'blob' })
  if (!(response.data instanceof Blob) || !response.data.type.startsWith('image/')) throw new Error('头像内容无效')
  return URL.createObjectURL(response.data)
}
