type PrintColumn = { prop: string; label: string }

function escapeHtml(value: unknown): string {
  return String(value ?? '').replace(
    /[&<>"']/g,
    (char) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      })[char]!
  )
}

/** 只输出文本字段，防止单据备注等内容被当作 HTML 执行。 */
export function buildPrintDocument(
  title: string,
  columns: PrintColumn[],
  rows: Record<string, unknown>[]
) {
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
    <style>body{font:14px sans-serif;color:#222;padding:24px}h1{font-size:22px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #888;padding:8px;text-align:left;overflow-wrap:anywhere}@page{size:A4 landscape;margin:12mm}</style>
    </head><body><h1>${escapeHtml(title)}</h1><table><thead><tr>${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join('')}</tr></thead>
    <tbody>${rows.map((row) => `<tr>${columns.map((column) => `<td>${escapeHtml(row[column.prop])}</td>`).join('')}</tr>`).join('')}</tbody></table></body></html>`
}

export function printDocument(
  title: string,
  columns: PrintColumn[],
  rows: Record<string, unknown>[]
) {
  const frame = document.createElement('iframe')
  frame.title = title
  frame.style.cssText = 'position:fixed;left:-10000px;top:0;width:1120px;height:800px;border:0'
  frame.onload = () => {
    const printWindow = frame.contentWindow
    if (!printWindow) {
      frame.remove()
      return
    }
    printWindow.addEventListener('afterprint', () => frame.remove(), { once: true })
    printWindow.focus()
    printWindow.print()
    // 部分浏览器不触发 afterprint，兜底回收隐藏文档。
    setTimeout(() => frame.remove(), 60000)
  }
  frame.srcdoc = buildPrintDocument(title, columns, rows)
  document.body.appendChild(frame)
}
