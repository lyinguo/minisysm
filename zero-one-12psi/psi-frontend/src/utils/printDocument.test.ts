import { describe, expect, it } from 'vitest'
import { buildPrintDocument } from './printDocument'

describe('document printing', () => {
  it('includes the selected document and escapes user supplied content', () => {
    const html = buildPrintDocument(
      '调拨单',
      [
        { prop: 'number', label: '单据编号' },
        { prop: 'remark', label: '备注' }
      ],
      [{ number: 'DB-001', remark: '<img src=x onerror=alert(1)>' }]
    )
    expect(html).toContain('DB-001')
    expect(html).toContain('&lt;img')
    expect(html).not.toContain('<img')
  })
})
