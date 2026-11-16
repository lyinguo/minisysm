import { describe, expect, it } from 'vitest'
import { permissionCatalog, readPermissionSelection, writePermissionSelection } from './permissionTree'

const raw = [
  { id: '085', name: '采购', children: [{ id: '086', name: '订单', children: [{ id: '112', name: '新增' }, { id: 'purchase_supply_manage', name: '供货关系' }] }] },
  { id: '112', name: '与新增功能重名的菜单', children: [{ id: '123', name: '财务', children: [{ id: '223', name: '修改付款' }] }] }
]

describe('actual role permission wire format', () => {
  it('separates colliding menu/function IDs and preserves named permission IDs', () => {
    const tree = permissionCatalog(raw)
    const wire = writePermissionSelection(['menu:085', 'menu:112', 'function:112', 'function:purchase_supply_manage'], tree)
    expect(wire).toEqual([{ id: '085', children: [{ id: '086', fun: [{ id: '112' }, { id: 'purchase_supply_manage' }] }] }])
    expect(readPermissionSelection(JSON.stringify(wire), tree)).toEqual({ keys: ['function:112', 'function:purchase_supply_manage'], notice: '' })
  })
  it('does not infer grants from checked or half-checked parent menus', () => {
    expect(writePermissionSelection(['menu:085', 'menu:086', 'menu:112'], permissionCatalog(raw))).toEqual([])
  })
  it('does not guess ambiguous legacy boolean selections or truthy strings', () => {
    const result = readPermissionSelection('{"112":true,"purchase_supply_manage":true,"223":"true"}', permissionCatalog(raw))
    expect(result.keys).toEqual(['function:purchase_supply_manage'])
    expect(result.notice).toContain('重名')
  })
  it('retains canonical check state even where legacy IDs collide', () => {
    const result = readPermissionSelection([{ id: '085', children: [{ id: '086', fun: [{ id: 112 }] }] }], permissionCatalog(raw))
    expect(result).toEqual({ keys: ['function:112'], notice: '' })
  })
  it('explains missing or malformed historical grants without granting replacements', () => {
    expect(readPermissionSelection('[{"fun":[{"id":"removed"}]}]', permissionCatalog(raw)).notice).toContain('不在当前目录')
    expect(readPermissionSelection('bad json', permissionCatalog(raw)).keys).toEqual([])
  })
})
