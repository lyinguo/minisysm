import { describe, expect, it } from 'vitest'
import { utils, write } from 'xlsx'
import { parseWarehouseWorkbook, warehouseHeaders } from './masterWorkbook'
import { integrityMessage } from './integrityMessage'
function file(rows: unknown[][]) {
  const book = utils.book_new()
  utils.book_append_sheet(book, utils.aoa_to_sheet(rows), '仓库')
  return write(book, { type: 'array', bookType: 'xlsx' })
}
describe('warehouse workbook and integrity errors', () => {
  it('reads a matching template without changing numeric identifiers', () => {
    expect(parseWarehouseWorkbook(file([warehouseHeaders, ['001', '仓库', '联系人', '00123', '地址', '备注']]))[0])
      .toMatchObject({ number: '001', name: '仓库', tel: '00123', data: '备注' })
  })
  it('rejects mismatched headers and duplicate codes', () => {
    expect(() => parseWarehouseWorkbook(file([['客户名称']]))).toThrow('表头不匹配')
    expect(() => parseWarehouseWorkbook(file([warehouseHeaders, ['001', '甲'], ['001', '乙']]))).toThrow('重复')
  })
  it('turns database guard errors into business reasons without exposing SQL', () => {
    expect(integrityMessage({ message: 'SQL: PSI_INTEGRITY:referenced:supplier:buy' })).toContain('供应商已被')
    expect(integrityMessage('PSI_INTEGRITY:balance:customer')).toContain('未结清余额')
    expect(integrityMessage('PSI_INTEGRITY:cycle:menu')).toContain('不能将自身或下级')
    expect(integrityMessage({ code: 10000, data: [] })).toBeUndefined()
  })
})
