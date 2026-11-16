export interface PermissionNode {
  id: string
  resourceId: string
  name: string
  kind: 'menu' | 'function'
  disabled?: boolean
  children?: PermissionNode[]
}

export function permissionCatalog(raw: any[]): PermissionNode[] {
  const seen = new Set<string>()
  const node = (value: any, kind: PermissionNode['kind']): PermissionNode => {
    const resourceId = String(value?.id ?? '')
    if (!resourceId) throw new Error('权限目录缺少标识，请刷新后重试')
    const id = `${kind}:${resourceId}`
    if (seen.has(id)) throw new Error('权限目录含重复节点，请检查菜单配置')
    seen.add(id)
    return { id, resourceId, kind, name: String(value.name ?? resourceId), disabled: kind === 'function' && String(value.is_enable ?? '1') !== '1' }
  }
  return raw.map(main => ({ ...node(main, 'menu'), children: (main.children ?? []).map((sub: any) => ({
    ...node(sub, 'menu'), children: (sub.children ?? []).map((item: any) => node(item, 'function'))
  })) }))
}

export function readPermissionSelection(raw: unknown, tree: PermissionNode[]) {
  const functions = new Map<string, string>(), menus = new Set<string>()
  const visit = (nodes: PermissionNode[]) => nodes.forEach(item => {
    if (item.kind === 'function') functions.set(item.resourceId, item.id)
    else menus.add(item.resourceId)
    if (item.children) visit(item.children)
  })
  visit(tree)
  const selected = new Set<string>(), ambiguous = new Set<string>(), unknown = new Set<string>()
  let root: any
  try { root = typeof raw === 'string' ? JSON.parse(raw || '[]') : raw ?? [] }
  catch { return { keys: [], notice: '原权限记录格式无效。仅修改名称或备注会保留原记录；修改权限前请重新核对勾选。' } }
  const add = (id: string) => {
    const key = functions.get(id)
    if (key) selected.add(key)
    else unknown.add(id)
  }
  if (Array.isArray(root)) {
    const collect = (nodes: any[], depth: number) => {
      if (depth > 64) throw new Error('权限层级过深')
      for (const item of nodes) {
        if (Array.isArray(item?.fun)) for (const permission of item.fun) if (permission?.id != null) add(String(permission.id))
        if (Array.isArray(item?.children)) collect(item.children, depth + 1)
      }
    }
    try { collect(root, 0) } catch { return { keys: [], notice: '原权限层级异常，请重新核对功能权限。' } }
    return { keys: [...selected], notice: unknown.size ? `有${unknown.size}项原权限不在当前目录。仅修改名称或备注会保留原记录；修改权限前请核对勾选。` : '' }
  }
  if (root && typeof root === 'object') {
    for (const [id, value] of Object.entries(root)) {
      if (value !== true) continue
      if (menus.has(id) && functions.has(id)) ambiguous.add(id)
      else if (!menus.has(id)) add(id)
    }
    const populated = Object.values(root).some(value => value === true)
    return { keys: [...selected], notice: populated ? `这是旧版权限记录${ambiguous.size ? `，其中${ambiguous.size}项菜单与功能标识重名，未自动勾选` : ''}。请核对功能勾选后保存；仅修改名称或备注会保留原记录。` : '' }
  }
  return { keys: [], notice: '原权限记录格式无效，请重新核对功能权限。' }
}

export function writePermissionSelection(keys: unknown[], tree: PermissionNode[]) {
  const selected = new Set(keys.map(String))
  const result: Array<{ id: string; children: Array<{ id: string; fun: Array<{ id: string }> }> }> = []
  for (const main of tree) {
    const children = []
    for (const sub of main.children ?? []) {
      const fun = (sub.children ?? []).filter(item => item.kind === 'function' && selected.has(item.id)).map(item => ({ id: item.resourceId }))
      if (fun.length) children.push({ id: sub.resourceId, fun })
    }
    if (children.length) result.push({ id: main.resourceId, children })
  }
  return result
}
