import { useHttp } from '@/plugins/http'

export interface BackupStatus { database: string; tables: number; format: string; scope: string }
export function getBackupStatus() { return useHttp().get<BackupStatus>('/homepage/system/backup/status', {}, { timeout: 30000 }) }
export async function downloadDatabaseBackup() {
  const response = await useHttp().getFile('/homepage/system/backup/download', {}, { responseType: 'blob', timeout: 180000 })
  const blob = response instanceof Blob ? response : response.data
  if (!(blob instanceof Blob) || blob.size === 0) throw new Error('未收到备份文件，请重试')
  if (blob.type.includes('json')) {
    const error = JSON.parse(await blob.text())
    throw new Error(error.message || error.data || '生成备份失败，请重试')
  }
  const disposition = response.headers?.['content-disposition'] || ''
  const match = /filename=([^;]+)/i.exec(disposition)
  return { blob, filename: match?.[1]?.replace(/"/g, '') || `minisysm-${Date.now()}.sql`, sha256: response.headers?.['x-backup-sha256'] || '' }
}
