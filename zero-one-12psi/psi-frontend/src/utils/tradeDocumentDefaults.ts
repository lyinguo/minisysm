import { generateBillNumber } from './billNumber'

export function tradeDocumentDefaults(kind: 'sale' | 'purchase', now = new Date()) {
  const date = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-')
  return { documentDate: date, documentNumber: generateBillNumber(kind === 'sale' ? 'XSD' : 'CGD') }
}
