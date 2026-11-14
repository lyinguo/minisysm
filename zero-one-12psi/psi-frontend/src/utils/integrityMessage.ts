const names: Record<string, string> = {
  customer: '客户', supplier: '供应商', goods: '商品', warehouse: '仓库', account: '资金账户',
  frame: '组织', people: '人员', role: '角色', menu: '菜单', dict_type: '字典类型', user: '用户'
}

export function integrityMessage(value: unknown): string | undefined {
  const text = typeof value === 'string' ? value : JSON.stringify(value ?? '')
  const match = text.match(/PSI_INTEGRITY:(\w+):(\w+)/)
  if (!match) return
  const [, rule, kind] = match
  const name = names[kind] || '资料'
  if (rule === 'balance') return `${name}存在未结清余额，不能删除`
  if (rule === 'referenced') return `${name}已被单据、库存或其他资料引用，不能删除，请保留历史资料`
  if (rule === 'missing') return `${name}已不存在，请刷新后重新选择`
  if (rule === 'immutable') return `${name}的内部 ID 不允许修改`
  if (rule === 'cycle') return `${name}不能将自身或下级设置为上级`
  if (rule === 'reserved') return '内置管理员账号不能删除'
  if (rule === 'login') return '登录账号创建后不能修改，请保留历史制单人与日志关联'
  if (rule === 'readonly') return '功能参数尚未统一接入业务，暂不允许修改'
  if (rule === 'initial') return '资金账户已有业务流水，不能修改期初余额'
  return '操作违反数据关联规则，请刷新后重试'
}
