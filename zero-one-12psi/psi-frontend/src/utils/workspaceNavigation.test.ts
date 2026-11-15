import { describe, expect, it } from 'vitest'
import { navigationEntries, usageGuide } from './workspaceNavigation'
import type { Menu } from '@/apis/login/type'

describe('workspace navigation', () => {
  it('searches only configured menu entries with existing local routes, including reports', () => {
    const menus: Menu[] = [{ id: 'root', text: '采购管理', icon: '', children: [
      { id: 'purchase', text: '采购单', icon: '', href: '/purchase-order', hasReport: true },
      { id: 'duplicate', text: '重复入口', icon: '', href: '/purchase-order' },
      { id: 'missing', text: '无效入口', icon: '', href: '/missing' },
      { id: 'external', text: '外部入口', icon: '', href: '//external.example' }
    ] }]
    const paths = new Set(['/purchase-order', '/purchase-order-report'])
    expect(navigationEntries(menus, path => paths.has(path))).toEqual([
      { path: '/purchase-order', label: '采购单', group: '采购管理' },
      { path: '/purchase-order-report', label: '采购单报表', group: '采购管理' }
    ])
    expect(navigationEntries([], () => true)).toEqual([])
  })
  it('uses explicit report destinations rather than inventing another suffix', () => {
    expect(navigationEntries([{ id: 'one', text: '采购', icon: '', href: '/purchase', hasReport: true, reportHref: '/report/purchase/summary' }], () => true).map(entry => entry.path))
      .toEqual(['/purchase', '/report/purchase/summary'])
  })
  it('explains template configuration and password preservation without claiming system-wide completion', () => {
    expect(usageGuide('/sysmanage/import').summary).toContain('具体业务页面下载模板')
    expect(usageGuide('/user-manage').steps.join('')).toContain('密码留空表示保持原密码')
    expect(usageGuide('/report/purchase/summary').group).toBe('报表查询')
  })
})
