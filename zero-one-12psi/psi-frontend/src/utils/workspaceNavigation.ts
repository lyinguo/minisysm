import type { Menu } from '@/apis/login/type'

export interface NavigationEntry { path: string; label: string; group: string }
export function navigationEntries(menus: Menu[], exists: (path: string) => boolean): NavigationEntry[] {
  const entries = new Map<string, NavigationEntry>()
  function add(path: string | undefined, label: string, group: string) {
    if (!path?.startsWith('/') || path.startsWith('//') || !exists(path)) return
    if (!entries.has(path)) entries.set(path, { path, label, group })
  }
  function visit(items: Menu[], parents: string[] = []) {
    for (const item of items) {
      const group = parents.join(' / ')
      add(item.href, item.text, group)
      if (item.hasReport) add(item.reportHref || (item.href ? item.href + '-report' : undefined), item.text + '报表', group)
      if (item.children?.length) visit(item.children, [...parents, item.text])
    }
  }
  visit(menus)
  return [...entries.values()]
}

export interface UsageGuide { group: string; summary: string; steps: string[]; note?: string }
const guides: Record<string, UsageGuide> = {
  '/system/backup': { group: '系统设置', summary: '生成并下载当前业务数据库的SQL备份，留存维护前的数据。', steps: ['使用系统管理员账号，检查Docker与MySQL备份环境。', '生成并下载备份，确认浏览器保存SQL文件。', '将备份妥善保管，恢复前先在独立空数据库中验证。'], note: '只备份数据库，不包含上传附件、Redis及服务配置；下载文件包含账号与业务数据，不应上传到公开仓库。' },
  '/dashboard': { group: '工作台', summary: '从业务入口开始，按资料准备、业务录入、结果查询的顺序使用系统。', steps: ['首次使用先维护组织、商品、仓库和往来单位。', '选择采购、销售或库存业务，录入单据并核对明细。', '在对应报表中按日期、单位和商品查看业务结果。'] },
  '/user-manage': { group: '账号与权限', summary: '维护系统登录账号，为用户选择所属组织和角色。', steps: ['先准备组织和角色，再点击“新增用户”。', '填写名称、登录账号、手机号和初始密码；组织和角色均需选择。', '点击“编辑”维护资料，修改已有用户时密码留空表示保持原密码。'], note: '登录账号创建后不能修改；被历史业务引用的用户不能直接删除。' },
  '/user-role': { group: '账号与权限', summary: '维护角色及其功能权限和数据范围，再将角色分配给用户。', steps: ['新增角色并填写容易识别的名称。', '按职责选择功能权限和数据范围，核对后保存。', '回到用户管理分配角色，再使用对应用户验证实际访问范围。'], note: '菜单是否显示、接口是否允许、数据范围是否受限，需要分别检查。' },
  '/customer-manage': { group: '基础资料', summary: '维护销售业务使用的客户、联系方式和往来资料。', steps: ['新增客户，填写名称、唯一编号、组织及必要联系信息。', '通过名称或编号查询客户，打开详情后维护资料。', '批量录入时先下载模板，按列填写后上传；导出前先选择记录。'], note: '已经关联单据或存在未结清余额的客户需要保留，不能直接删除。' },
  '/supplier-manage': { group: '基础资料', summary: '维护采购业务使用的供应商及联系方式。', steps: ['新增供应商并填写名称、编号和组织。', '在采购业务中选择已维护的供应商。', '批量录入前先下载本页面模板，填写后再导入。'], note: '已被业务引用或有未结清余额的供应商不能直接删除。' },
  '/sysmanage/import': { group: '系统配置', summary: '配置批量导入所使用的字段模板。日常导入请先到客户、供应商、商品等具体业务页面下载模板。', steps: ['先确认要导入哪一类资料。', '在对应业务页面下载空白 Excel 模板，保留列名并填写业务数据。', '回到该业务页面上传文件，按校验提示修正后重试。'], note: '这里用于维护模板规则；模板不是已经录入的业务数据。' },
  '/sysmanage/dictionary': { group: '系统配置', summary: '维护业务选项的分类和条目，例如类别、等级等基础选项。', steps: ['先选择字典类型，再查看该类型下的字典项。', '新增或修改条目时核对显示名称和取值。', '保存后回到使用该选项的业务页面检查显示。'], note: '调整正在使用的选项前，请先确认对历史资料的影响。' },
  '/sysmanage/menu': { group: '系统配置', summary: '维护导航名称、层级和页面入口，再结合角色配置菜单访问。', steps: ['选择上级菜单，确认新增位置。', '填写名称和有效页面路径，检查是否需要关联报表。', '保存后核对导航及角色权限配置。'], note: '菜单入口不等于业务功能或接口授权；有子菜单或关联权限时不能直接删除。' },
  '/fund-account': { group: '基础资料', summary: '维护收付款使用的资金账户，区分期初余额和业务产生的当前余额。', steps: ['新增账户并核对名称、编号、组织和期初余额。', '收款、付款和转账时选择对应资金账户。', '通过账户流水核对业务发生后的余额。'], note: '已有业务流水后不要用修改期初余额来调整当前余额。' }
}
export function usageGuide(path: string): UsageGuide {
  if (path === '/purchase-booking-report') return {
    group: '采购订单', summary: '查询完整采购订单，审核后按剩余数量生成采购草稿，再到采购单完成收货入库。',
    steps: ['按订单编号或业务条件查询，打开详情核对全部商品、供应商和金额。', '先审核采购订单；订单审核本身不会入库或付款。', '点击“生成→采购单”，核对已入库、待入库占用和可生成数量，填写本次数量及新采购单日期、编号。数量0表示本次不收该行。', '生成后自动打开采购单报表；在对应采购单详情核对、审核，才会实际入库并登记应付或付款。'],
    note: '未入库草稿仍占用订单数量；预览会列出已生成采购单，可点击继续处理。删除未核对、无关联的草稿后才能释放占用，不要重复开单。'
  }
  if (path === '/purchase-booking') return {
    group: '采购录入', summary: '先选商品，每行选择已建立供货关系的供应商，预览后按供应商拆单保存。',
    steps: ['添加实际商品，为每行选择供货商和入库仓库。', '商品没有可用供货商时，先向供应商确认，再点击该行“维护供货商”建立关系；普通采购权限不能代替供货关系管理权限。', '填写数量、单价、税率及日期，核对下方各家订单编号和金额。', '点击“按供应商拆单保存”；全部成功后列出订单编号，任一失败保留全部输入。'],
    note: '同一供应商的明细合并一单，不同供应商分别成单。保存的是未审核草稿，不代表已经收货入库或付款。'
  }
  if (guides[path]) return guides[path]
  if (path.startsWith('/report/') || path.endsWith('-report') || path === '/purchase-sales-cost') return {
    group: '报表查询', summary: '按日期和业务对象筛选记录，查看明细、汇总及相关单据。',
    steps: ['先确认查询日期和业务类型，再补充单位、仓库或商品等条件。', '执行查询，检查记录数量和汇总口径。', '需要逐笔核对时打开单据详情；导出、打印前确认当前筛选条件。'], note: '明细表用于逐笔追溯，汇总表用于分组统计；没有记录时先检查日期和筛选条件。'
  }
  if (/purchase|sales|receipt-order|payment-order|other-income|other-expense|transfer-account|writeoff/.test(path)) return {
    group: '业务单据', summary: '录入业务对象和单据明细，核对后保存，并按业务需要执行审核。',
    steps: ['先准备客户或供应商、商品、仓库和资金账户等关联资料。', '选择业务对象，填写日期、数量、单价及必要明细后保存。', '核对单据状态，再进行审核、收付款或后续处理；到对应报表检查结果。'], note: '保存和审核含义不同。已审核记录需按页面规则处理，操作前请确认库存和资金影响。'
  }
  if (/inventory|inbound|outbound|warehouse|transfer-order|batch|serial/.test(path)) return {
    group: '库存管理', summary: '按仓库和商品查看库存，或维护入库、出库、调拨及盘点业务。',
    steps: ['确认商品、仓库、批次或序列号等查询范围。', '查询页面按条件查看；单据页面先录入并核对明细。', '审核操作前确认数量及状态，操作后查询库存和相关记录。'], note: '调拨需要区分调出仓库和调入仓库；查询库存与修改库存是不同操作。'
  }
  if (/system|sysparams|parameter|number|period/.test(path)) return {
    group: '系统设置', summary: '查看和维护系统规则，调整前先确认适用业务及页面说明。',
    steps: ['阅读当前设置项说明，确认是否允许修改。', '核对变更对编号、期间和业务处理的影响后保存。', '在对应业务页面验证实际效果。'], note: '只读或标注待完善的规则不代表已经在全部业务中生效。'
  }
  return { group: '资料维护', summary: '查询已有资料，或新增、编辑业务需要的基础信息。', steps: ['先搜索已有记录，避免重复创建。', '新增时填写必填项，保存后重新查询并检查详情。', '批量操作先选择记录，导入时使用当前页面提供的模板。'] }
}
