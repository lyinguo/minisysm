import { describe, expect, it } from 'vitest'
import { tradeDocumentDefaults } from './tradeDocumentDefaults'

describe('new trade document defaults', () => {
  it('uses the local business date even just after midnight', () => {
    expect(tradeDocumentDefaults('sale', new Date(2026, 0, 2, 0, 5)).documentDate).toBe('2026-01-02')
  })
  it('generates separate bounded identifiers for new sales and purchase drafts', () => {
    const sale = tradeDocumentDefaults('sale').documentNumber
    const next = tradeDocumentDefaults('sale').documentNumber
    const purchase = tradeDocumentDefaults('purchase').documentNumber
    expect(sale).toMatch(/^XSD[A-Z0-9]+$/)
    expect(purchase).toMatch(/^CGD[A-Z0-9]+$/)
    expect(sale).not.toBe(next)
    expect(Math.max(sale.length, purchase.length)).toBeLessThanOrEqual(32)
  })
})
