/** 现金银行报表行映射 */
export function mapCashBankRow(item: Record<string, unknown>, index: number) {
  return {
    key: String(item.number ?? index),
    name: String(item.name ?? ''),
    extension: { type: String(item.type ?? '') },
    sourceData: {
      frameData: { name: String(item.frame ?? '') },
      time: item.time ? String(item.time).slice(0, 10) : '',
      number: String(item.number ?? ''),
      userData: { name: String(item.user ?? '') },
      data: String(item.data ?? '')
    },
    current: { name: String(item.customer ?? item.supplier ?? '') },
    in: Number(item.income) || 0,
    out: Number(item.expend) || 0,
    balance: Number(item.balance) || 0
  }
}

/** 通用分页结果 */
export function unwrapPage(res: { code?: number; data?: { rows?: unknown[]; total?: number }; message?: string }) {
  if (res?.code === 10000 && res.data) {
    return {
      rows: Array.isArray(res.data.rows) ? res.data.rows : [],
      total: Number(res.data.total) || 0
    }
  }
  throw new Error(res?.message || '请求失败')
}

/** 触发 openapi 导出 blob 下载 */
export function downloadExportBlob(res: unknown, fileName: string) {
  const anyRes = res as { data?: Blob } | Blob
  const blob: Blob | undefined =
    anyRes instanceof Blob
      ? anyRes
      : anyRes?.data instanceof Blob
        ? anyRes.data
        : undefined
  if (!blob) throw new Error('导出接口未返回有效文件，请重试')
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
