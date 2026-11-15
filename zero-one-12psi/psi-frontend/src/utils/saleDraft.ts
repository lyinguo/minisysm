import type { SaleDTO, SaleDocumentDetail } from '@/apis/sales/order/type'

export function saleEditorRows(document: SaleDocumentDetail): Record<string, any>[] {
  return document.items.map(line => ({
    id: line.id, original: { ...line }, goodsId: line.goods, productName: line.goodsName || line.goods,
    productCode: line.goodsNumber || '', spec: line.spec || '', attr: line.attr || '', unit: line.unit || '',
    warehouse: line.warehouse || '', warehouseName: line.warehouseName || '', price: Number(line.price), quantity: Number(line.nums),
    discount: Number(line.discount) > 1 ? Number(line.discount) / 100 : Number(line.discount) || 1, amount: Number(line.total),
    taxRate: Number(line.tax) > 1 ? Number(line.tax) : Number(line.tax) * 100,
    taxAmount: Number(line.tat), total: Number(line.tpt), remark: line.data || ''
  }))
}

export function saleEditorPayload(document: SaleDocumentDetail, header: Record<string, any>, customerId: string, rows: Record<string, any>[], form: Record<string, any>): SaleDTO {
  const date = String(header.documentDate || '').slice(0, 10)
  const originalDate = String(document.header.time || '').slice(0, 10)
  const originalTime = String(document.header.time || '').replace('T', ' ').slice(11, 19) || '00:00:00'
  const time = date === originalDate && document.header.timeEpoch != null ? Number(document.header.timeEpoch)
    : Date.parse(`${date}T${originalTime}+08:00`)
  if (!Number.isFinite(time)) throw new Error('请选择有效单据日期')
  const files = form.documentAttachment || []
  if (files.some((file: any) => !file.url || (file.status && file.status !== 'success'))) throw new Error('附件尚未上传成功，请重试或移除失败附件')
  return {
    ...document.header, id: String(document.header.id), version: document.version,
    frame: header.frame, customer: customerId, time, number: header.documentNumber,
    money: Number(form.receivedAmount ?? document.header.money ?? 0), cost: Number(form.documentFee ?? document.header.cost ?? 0),
    account: form.settlementAccount || '', people: form.relatedPerson || '',
    logistics: typeof form.logistics === 'string' ? form.logistics : JSON.stringify(form.logistics || {}),
    file: JSON.stringify(files.map((file: any) => ({ name: file.name || '', url: file.url }))), data: form.remarks || '',
    examine: false, check: false,
    items: rows.filter(row => row.productName).map(row => ({
      ...row.original, id: row.id || undefined, pid: String(document.header.id), goods: String(row.goodsId || ''),
      attr: row.attr || '', unit: row.unit, warehouse: row.warehouse,
      price: Number(row.price), nums: Number(row.quantity), discount: Number(row.discount) || 1,
      tax: Number(row.taxRate || 0) / 100, data: row.remark || ''
    }))
  }
}
