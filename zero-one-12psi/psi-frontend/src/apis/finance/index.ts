import { useHttp } from '@/plugins/http'

const http = useHttp()

/** 收款单 */
export const ReceiptAPI = {
  list: (body: Record<string, unknown>) => http.post('/fund/receipt/fundReceiptList', body),
  detail: (id: string) => http.post(`/fund/receipt/fundReceiptDetail?id=${encodeURIComponent(id)}`),
  add: (body: unknown) => http.post('/fund/receipt', body),
  update: (id: string, body: unknown) => http.put(`/fund/receipt/${id}`, body),
  audit: (body: unknown) => http.patch('/fund/receipt/audit', body),
  remove: (body: unknown) => http.delete('/fund/receipt', body),
  exportSimple: () => http.getFile('/fund/receipt/export/simple'),
  exportDetail: () => http.getFile('/fund/receipt/export/detail')
}

/** 付款单 */
export const PaymentAPI = {
  list: (params: Record<string, unknown>) => http.get('/payment-order/query-all', params),
  detail: (id: string) => http.get(`/payment-order/query-by-id/${encodeURIComponent(id)}`),
  add: (body: unknown) => http.post('/payment-order/add', body),
  update: (body: unknown, id: string) => http.put(`/payment-order/modify?id=${encodeURIComponent(id)}`, body),
  audit: (ids: string[]) => http.put('/payment-order/modify-examine-status', ids),
  remove: (ids: string[]) => http.delete('/payment-order/remove', ids)
}

/** 核销单 */
export const WriteoffAPI = {
  pendingBills: (params: Record<string, unknown>) => http.get('/verification-sheet/list/pending-bills', params),
  writtenBills: (params: Record<string, unknown>) => http.get('/verification-sheet/list/bill-written', params),
  getBill: (id: string) => http.post(`/verification-sheet/bill/get?id=${encodeURIComponent(id)}`),
  save: (body: unknown) => http.post('/verification-sheet/bill/save', body),
  update: (body: unknown) => http.post('/verification-sheet/bill/update', body),
  approve: (body: unknown) => http.post('/verification-sheet/approve', body)
}

/** 转账单 */
export const TransferAPI = {
  list: (params: Record<string, unknown>) => http.get('/allot/getAllotList', params),
  detail: (params: Record<string, unknown>) => http.get('/allot/getAllotDetail', params),
  add: (body: unknown) => http.post('/allot/addAllot', body),
  update: (body: unknown) => http.put('/allot/updateAllot', body),
  audit: (ids: string[], examine: number) =>
    http.put('/allot/examineAllots', ids, { params: { examine } })
}
