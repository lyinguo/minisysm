import type { PurchaseDocument } from '@/apis/purchase/purchaseOrder/type'

const number = (value: any) => Number(value) || 0
const round = (value: number) => Number(value.toFixed(4))
export function purchaseEditorRows(document: PurchaseDocument) {
  return document.items.map(item => {
    const gross = number(item.price) * number(item.nums)
    let serials: any[] = []
    try { const parsed = JSON.parse(item.serial || '[]'); serials = Array.isArray(parsed) ? parsed : [] } catch { /* Keep original metadata until explicitly edited. */ }
    return {
      ...item, goodsId: String(item.goods), productName: item.goodsName || item.goods,
      productCode: item.goodsNumber || '', spec: item.spec || '', warehouseName: item.warehouseName || item.warehouse,
      warehouse: String(item.warehouse || ''), price: number(item.price), quantity: number(item.nums),
      effectiveDiscount: gross ? round(number(item.dsc) / gross * 100) : number(item.discount),
      amount: number(item.total), taxRate: number(item.total) ? round(number(item.tat) / number(item.total) * 100) : number(item.tax),
      taxAmount: number(item.tat), total: number(item.tpt), remark: item.data || '',
      serialText: serials.map(value => typeof value === 'object' ? value.number : value).join(', ')
    }
  })
}
export function recalculatePurchaseRow(row: Record<string, any>) {
  row.amount = round(number(row.price) * number(row.quantity) * (1 - number(row.effectiveDiscount) / 100))
  row.taxAmount = round(number(row.amount) * number(row.taxRate) / 100)
  row.total = round(number(row.amount) + number(row.taxAmount))
}
export function purchaseEditorPayload(document: PurchaseDocument, header: Record<string, any>, supplier: string, rows: Record<string, any>[], form: Record<string, any>) {
  const valid = rows.filter(row => row.productName)
  if (!supplier) throw new Error('请选择供应商')
  if (!valid.length) throw new Error('至少保留一条商品明细')
  if (!header.documentDate || !header.documentNumber?.trim()) throw new Error('请填写单据日期和编号')
  const files = form.documentAttachment || []
  if (files.some((file: any) => !file.url || file.status && file.status !== 'success')) throw new Error('附件尚未上传成功，请重试或移除失败附件')
  const originalTime = String(document.header.time_text || document.header.time || '').replace('T', ' ')
  const time = header.documentDate + ' ' + (originalTime.slice(11, 19) || '00:00:00')
  const money = number(form.paidAmount)
  if (money > 0 && !form.settlementAccount) throw new Error('填写实付金额时请选择结算账户')
  const optional = (value: any, original: any) => !value && original == null ? undefined : String(value || '')
  let originalFiles: any[] = []
  if (document.header.file) {
    try { const parsed = JSON.parse(document.header.file); originalFiles = Array.isArray(parsed) ? parsed : [] }
    catch { originalFiles = String(document.header.file).split(',').filter(Boolean).map(url => ({ url, name: url.split('/').pop() })) }
  }
  const storedFiles = files.map((file: any) => ({ name: file.name || file.url.split('/').pop(), url: file.url }))
  const file = JSON.stringify(storedFiles) === JSON.stringify(originalFiles.map(file => ({ name: file.name || file.url?.split('/').pop(), url: file.url })))
    ? document.header.file ?? undefined : JSON.stringify(storedFiles)
  let logistics: any = form.logistics
  if (typeof logistics === 'object') {
    if (!logistics?.number) logistics = document.header.logistics == null ? undefined : ''
    else if (logistics.number === document.header.logistics) logistics = document.header.logistics
    else logistics = JSON.stringify(logistics)
  } else logistics = optional(logistics, document.header.logistics)
  return {
    id: String(document.header.id), version: document.version,
    supplier, time, number: header.documentNumber.trim(), money,
    account: optional(form.settlementAccount, document.header.account), people: optional(form.relatedPerson, document.header.people),
    file, logistics, data: optional(form.remarks, document.header.data),
    details: valid.map((row, index) => {
      if (!row.goodsId || !row.warehouse || !row.unit || number(row.quantity) <= 0 || number(row.price) < 0) throw new Error(`请检查第 ${index + 1} 行商品、仓库、单位、数量和单价`)
      const existing = !!row.id
      let serial: string | undefined = existing && row.serial == null ? undefined : typeof row.serial === 'string' ? row.serial : JSON.stringify(row.serial || [])
      if (row.serialText != null) {
        const edited = String(row.serialText).split(/[,，\n]/).map(value => value.trim()).filter(Boolean)
        let original: string[] = []
        try { original = JSON.parse(row.serial || '[]').map((value: any) => typeof value === 'object' ? value.number : String(value)) } catch { /* Explicit editor input replaces invalid legacy text. */ }
        if (JSON.stringify(edited) !== JSON.stringify(original)) serial = JSON.stringify(edited)
      }
      return { id: row.id || undefined, goods: String(row.goodsId), warehouse: String(row.warehouse), unit: String(row.unit), price: number(row.price), nums: number(row.quantity), discount: number(row.effectiveDiscount), tax: number(row.taxRate), data: optional(row.remark, row.data), retreat: 0,
        source: existing && row.source == null ? undefined : row.source || '0', attr: existing && row.attr == null ? undefined : row.attr || '',
        batch: existing && row.batch == null ? undefined : row.batch || '', mfd: existing && row.mfd == null ? undefined : row.mfd || '',
        serial }
    })
  }
}
