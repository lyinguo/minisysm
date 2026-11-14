/**
 * 资金单据请求体规范化：日期、附件字段兼容后端类型
 */

/** 日期转 LocalDateTime 字符串（兼容仅日期） */
export function toDateTime(value?: string | null): string {
  if (!value) return ''
  let text = String(value).trim().replace('T', ' ')
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return `${text} 00:00:00`
  }
  if (text.length >= 19) {
    return text.slice(0, 19)
  }
  return text
}

/** 日期转 yyyy-MM-dd（LocalDate） */
export function toDateOnly(value?: string | null): string {
  if (!value) return ''
  return String(value).trim().slice(0, 10)
}

function extractFileToken(file: unknown): string {
  if (!file) return ''
  if (typeof file === 'string') return file
  if (typeof file === 'object') {
    const f = file as Record<string, any>
    return String(f.url || f.name || f.response?.info || f.response?.data || '')
  }
  return ''
}

/** 附件：后端要 String 时取第一个或 JSON；要 List 时返回字符串数组 */
export function toFileField(files: unknown, mode: 'string' | 'array' = 'string'): string | string[] {
  const list = (Array.isArray(files) ? files : files ? [files] : [])
    .map(extractFileToken)
    .filter(Boolean)
  if (mode === 'array') return list
  if (list.length === 0) return ''
  if (list.length === 1) return list[0]
  return JSON.stringify(list)
}
