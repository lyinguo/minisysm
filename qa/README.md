# 系统业务验收

## 逐行供应商及自动拆单

`python qa/purchase_split_acceptance.py run` 执行8项实际接口/数据库/权限/并发/故障回滚专项。采购服务启动自动建立psi_goods_supplier，独立迁移见database/migrations/20261115_goods_supplier.sql；不迁入历史推断关系。每个组织单独维护商品与供应商多对多关系，维护权限资源为/purchase-order/supply/manage，新增/查询选项用现有/purchase-order/add。普通采购授权不意味着可改变供货清单。脚本仅向严格绑定QA库及18023服务写入，新角色测试只临时修改QA Redis并恢复。

运行该脚本prepare后，在隔离页面添加输出的两种商品：第一行选QA Supply A，第二行通过“维护供货商”查询并建立QA Supply B关系。各数量1、税率0、单价100/75，仓库选打印的唯一名称，采购编号使用打印值。保存生成两单，执行verify独立核对SQL。选择供货商和仓库后可先切换供应商资料页再返回，检查逐行输入保留。测试资料、会话和截图不发布。此流程不证明订单后续审核/导入/生成采购单或采购单直接开单的供货约束已完成。

## 采购订单供应商入口专项

`python qa/booking_supplier_acceptance.py run` 通过18021专用基础资料服务实际新增12个供应商，验证名称和编号分别查询、10条分页完整返回全部真实UUID，并独立核对数据库。查询及分页仍可用于商品供货维护中的真实供应商选择窗口；此前顶部整单供应商、漏选直接打开窗口的浏览器记录属于历史页面，当前采购录入请执行本文开头的逐行拆单专项。

界面回归包括真实工作区HomeView的标签切换重新挂载；旧实现先等仓库接口再恢复草稿，会在中途卸载时把空值覆盖原供应商，普通单组件挂载测试不能复现。保留精确UUID断言验证同步恢复。此专项只证明供应商查询、选择及前端草稿保留，不证明采购订单完整保存/审核/来源链、全部资料权限或附件完成。

## 数据备份与恢复专项

`prepare_oauth_build.py --module psi-j1-homepage` 构建独立homepage-project，`start_java_test.ps1 -Service homepage` 在18025启动。`python qa/backup_acceptance.py run` 真实验证管理员权限、撤权、状态检查及SQL下载；将备份恢复到新建的严格psi_qa_名称数据库，核对全部表数量、真实采购入账的库存/资金/应付及精确文本/二进制和触发器，最后清理本次新恢复库。不要与其他QA写入测试同时运行，以保证前后对比一致。

故障专项：先确认并停止专用homepage进程，使用 `-Service homepage -BackupContainer qa-backup-missing-20261115` 启动同一候选，执行 `python qa/backup_acceptance.py unavailable`；不停止真正MySQL容器。验证后恢复无覆盖参数的正常QA候选。浏览器先执行该脚本 `prepare`，进入隔离页面“系统配置→数据备份”，验证失败提示、环境重试、实际SQL下载，并独立核对页面SHA256。下载SQL、会话、日志和恢复库数据一律不发布。

正常本地环境通过 `/system/backup` 使用，接口 `/homepage/system/backup/status` 和 `/download` 只允许当前数据库role=0的系统管理员。默认Docker容器mysql8；其他部署需配置 `psi.backup.container`，并保证服务能运行Docker CLI和容器内mysqldump、容器环境提供MySQL认证。导出只处理当前业务数据库，超时或容器/数据库身份不匹配拒绝；不提供自动恢复或上传覆盖数据库操作。复杂视图/例程/事件及跨版本恢复需单独验收。

## 核心收付款优先：付款草稿专项

使用 `prepare_oauth_build.py --module psi-j6-payment_order` 构建独立 `payment-project`，随后 `start_java_test.ps1 -Service payment` 仅在18024端口启动。与其余QA服务共用专用测试库和18379 QA Redis；写入保护要求服务名和固定端口同时匹配，不能仅凭端口范围判断隔离。

运行 `python qa/payment_draft_acceptance.py` 验证8项实际OAuth/HTTP/MySQL付款草稿场景：真实组织/制单人和明细总额、逐行金额校验、资料存在性、重复/并发编号、第二明细真实存储故障回滚及重试、授权/撤权/跨组织、伪造身份、四位金额/附件元数据和状态伪造。基础资料和故障触发器为显式QA夹具，不直接伪造业务入账。含文件JSON的列直接读取核对，避免MySQL命令行对嵌套JSON额外转义影响测试解析。

此专项不证明付款修改/审核/反审核/核销、页面链及独立收款完成。整条付款链尚未真实验收前保留为QA候选，不替换正常付款服务；后续按核心优先级继续修复。

## 采购Excel导入专项

运行 `python qa/purchase_import_acceptance.py run` 执行11项实际模板/文件上传/持久化/回滚/并发/权限与入账验收，需要本地安装openpyxl。表头和指南从实际接口下载，填写后真实上传，不通过SQL伪造导入结果；主资料、外组织及故障触发器是仅限QA的显式测试夹具。与其他资源授权程序串行运行，任意失败保持未完成。

页面验收先执行 `prepare` 创建私有有效/无效工作簿及会话，在隔离页面“采购单报表→批量”实际下载模板，先上传 `qa/runtime/purchase-import-browser-invalid.xlsx`，确认第4行错误持续可见，运行 `verify-rejected`。再上传 `purchase-import-browser.xlsx`，查询输出编号、打开详情后运行 `verify-saved` 独立核对2条明细及300/339/实付0、库存资金不变。工作簿、会话、报告、SQL结果和截图不发布；禁止在正常业务库执行写入验收。

## 采购入口授权专项

运行 `python qa/purchase_security_acceptance.py`，使用真实新建角色用户的 OAuth 凭据验证列表、新旧详情、退货数据预览、新增、修改、两类导出和 multipart 导入入口的权限；再验证组织边界、混合导出整批拒绝、实际 Excel 文件及原 token 撤权即时生效。动态详情沿用 `/purchase-note/info` 资源授权。只能操作经容器和端口核验的 QA Redis，并恢复原资源键；不要同时运行其他会修改这些键的验收程序。

导入测试提交必填文件字段，避免参数校验提前拒绝而未执行授权。它只证明无权请求在解析文件前被拒绝且不新增单据，不证明完整导入业务可用。角色管理页面到资源缓存刷新、完整菜单权限和采购其余生命周期仍待验收。

本目录是长期系统修复的验收入口。只读查询、页面冒烟、单元测试都不是业务完成证明。每个模块必须有实际 HTTP 操作、独立 MySQL 持久化断言、失败回滚及关联影响验证；权限功能还必须验证不同身份的允许与拒绝。

## 环境边界

- 业务写入仅允许发往 `127.0.0.1` 的专用测试端口，数据库名必须匹配 `psi_qa_` 前缀。
- 测试库从不含记录的 schema 创建，启用与运行环境相同的完整性迁移。
- 测试服务禁止注册到运行环境的 Nacos 服务列表，防止真实请求进入测试服务或测试写入进入现有服务。
- 不复制真实客户、供应商、单据、资金、库存数据。不改动现有账号、角色授权。
- `.state.json`、`reports/`、`runtime/` 只保存在本地，不发布。认证凭据从环境或本地私有配置读取，报告不输出令牌和密码。

## 完成标准

验收状态为 `pending`（尚未执行）、`failed`（已复现失败）、`blocked`（依赖未满足）、`verified`（约定的业务断言全部通过）。仅跑通一个接口，不能将整个模块改为 verified。每次修复后需重跑失败场景和受到影响的业务链。

具体功能和状态见 `ACCEPTANCE.md`。结果写入本地 `reports/`。本任务在所有约定功能通过实际业务验收前保持进行中，不以局部修复作为全系统交付。

## 库存与商品选择专项

已有隔离 C1、OAuth、MySQL 环境后，可用 `prepare_oauth_build.py --module psi-j2-storemanagement`／`--module psi-j6-basic_Information` 生成独立 Maven 工程，构建后用 `start_java_test.ps1 -Service store`／`basic` 启动。专用端口分别为 18020、18021；共享依赖须先从当前源码安装，不能混用旧 API 签名。

运行 `python qa/warehouse_acceptance.py baseline`、`python qa/warehouse_acceptance.py lifecycle` 及 `python qa/product_selection_acceptance.py` 执行实际接口验收。商品／仓库测试夹具和新增账号仅存在于专用数据库；这些测试不代表完整权限、所有库存单据或浏览器保存流程已经通过。仓储新接口和安全修改目前仍以隔离环境验证为主，部署状态应单独核对。

采购、销售查询验收使用 `psi-j3-purchase`、`psi-sale` 独立工程，分别通过 `start_java_test.ps1 -Service purchase`／`sale` 启动在 18023、18022，运行 `python qa/trade_query_acceptance.py`。查询夹具通过受限SQL准备；这只能证明查询与组织选项，不代表单据新增、审核或资金库存链已完成。Java私有配置必须同时覆盖 `spring.datasource` 与 `spring.datasource.druid`，启动脚本拒绝不属于专用库的JDBC地址。

## 销售草稿专项

在专用 sale 服务运行后，分别执行 `python qa/sale_draft_acceptance.py baseline`、`python qa/sale_draft_acceptance.py lifecycle`、`python qa/sale_draft_acceptance.py security`。测试真实创建新账号和销售草稿，并验证持久化、版本冲突、回滚及权限撤销；权限数据仅调整专用 QA Redis，结束恢复原测试键。不能指向运行环境 Redis。

`python qa/sale_schema_acceptance.py` 另建临时空库并实际启动候选服务，验证旧 DECIMAL(5,2) 税率/折扣字段自动扩为 DECIMAL(7,4)，已有数值不变；不把历史百分数自动重写为比例。源码迁移位于 `database/migrations/20261115_sale_rate_precision.sql`。审核、库存和资金联动仍须独立验收。

## 销售审核与资金库存基线

运行 `python qa/sale_posting_acceptance.py`。每个场景重新建立专用资料，通过真实库存入库接口准备数量，再通过销售新增、核对、审核接口检查真实库存、应收、账户、流水、反审核、批量与并发。当前已复现6项失败，命令返回非零是拒绝交付的验收结果，不能删除断言或改成仅检查审核状态来消除失败。销售服务与库存服务必须连接同一个专用QA数据库，库存服务不能指向现有业务端口。

销售审核修复的扩展验收运行 `python qa/sale_posting_extended.py`。成本模式测试要求专用库没有已有 `fun` 配置；仅为测试夹具临时保存、移除并精确恢复该库的两个配置只读触发器，退出时清理自建配置。这是成本引擎验证，不证明系统参数写入功能已实现。不要在运行环境执行这些夹具。

浏览器验收先运行 `python qa/sale_browser_acceptance.py prepare`，用隔离 UI 查询打印出的编号，打开详情并核对、审核；执行 `verify-audited` 独立核对SQL，再在页面反审核后执行 `verify-reversed`。会话、单据标识、结果和截图只保存在私有 runtime/reports，不能发布。

入账顺序由 `psi_stock_posting_order` 的数据库序号保存，同一业务时间的后入库记录不能因为随机ID排到先入库记录前。新增销售、库存服务必须一起更新以覆盖新收发流水；旧流水缺失顺序的历史歧义不会自动修复。`psi_sale_posting` 用于确认本实现的入账凭据；历史仅改状态而没有完整凭据的已审核销售单，不允许自动重新入账或凭空反冲。

## 采购草稿保存专项

运行 `python qa/purchase_draft_acceptance.py`。测试通过真实采购新增接口与独立SQL检查UUID供应商、可选批次日期、附件/序列号元数据、未付款及零费用状态、编号重复/并发、严格日期、第二条明细故障回滚、仓库组织和伪造身份拒绝。商品、供应商、仓库与账号夹具仅新建在专用库；不代表附件文件上传下载、完整角色授权、金额重算、修改、采购审核/入库/应付/付款或完整页面开单已经通过。

## 采购修改专项

运行 `python qa/purchase_revision_acceptance.py`。流程为实际创建采购草稿，GET `/purchase-note/document/{id}` 读取完整 `header/items/version`，POST `/purchase-note/revise` 提交 `id/version/details` 和需要修改的头字段，再独立核对MySQL。新建明细不带ID；保留的明细提交原ID；省略原明细表示删除，因此保存必须基于完整读取的版本。缺少版本或版本已过期会被拒绝。

该旧修改DTO的折扣/税率使用百分数（例如13表示13%）；原记录存在比例表示时，未修改的比例须与原始折扣额/税额相符，按原有效比例计算，不能静默重新解释历史金额。修改不能设置审核或核对状态，也不能直接修改已核对、审核或有关联凭据的单据。接口测试不证明采购页面已接入真实编辑，完整角色授权和采购审核资金库存链仍需验收。

## 采购页面专项复现

运行 `python qa/purchase_ui_acceptance.py run` 验证真实名称、关联查询、组织数据范围、Excel内容和新增行元数据。所有写入限定专用QA库和18023采购服务。功能级角色授权、采购审核及资金库存链另行验收，不包含在这4项中。

浏览器先运行 `python qa/purchase_ui_acceptance.py prepare`，在隔离UI采购单报表查询输出编号，详情数量2改3保存后运行 `verify-edit`。重新打开改4但不保存，运行 `advance-version` 模拟另一请求保存5，再从旧页面保存，应提示版本冲突且保留输入4；执行 `verify-conflict` 确认SQL仍为5。页面重新加载读取5后改3保存，再执行 `verify-edit`。私有会话、单据ID、导出文件及截图不发布。

## 采购核对/审核专项

运行 `python qa/purchase_posting_acceptance.py check` 验证核对事务、真实存储故障回滚/重试、组织与角色授权。`posting` 验证实际入库、应付、部分付款和反审核；修复前4项失败，修复进展见下节；任何非零退出仍必须保留为未完成证据。默认 `all` 执行全部，不能只运行check便宣称采购审核通过。

沿用采购页面专项的数量3草稿，在真实浏览器点击核对后运行 `verify-checked`，点击反核对后运行 `verify-unchecked`，独立验证状态及库存资金不变量。正常业务环境不运行任何这些写入测试。

## 采购入账修复与成本联动

修复前采购审核4项失败基线现已通过。依次执行 `purchase_posting_acceptance.py all`、`purchase_posting_extended.py`、`purchase_posting_business.py`，共29项实际采购核对/入账验收；任一断言失败都必须保留失败状态。`sale_business_time_acceptance.py` 实际验证日期/完整时间/ISO/毫秒格式及非法日期不持久化。成本测试仅调整专用QA配置并恢复两条参数保护触发器，不代表系统参数管理完成。

浏览器运行 `python qa/purchase_browser_acceptance.py prepare`，按输出编号打开采购单报表，核对后审核，运行 `verify-audited` 独立核对库存/现金/应付/流水；页面反审核后运行 `verify-reversed`。夹具、token、SQL结果、截图及JAR均不发布。来源订单/发票SQL夹具、普通def成本规则和单仓测试不等同完整订单/发票生命周期或全部成本组合通过。

## 采购删除专项

运行 `python qa/purchase_delete_acceptance.py run` 执行11项真实删除/关联/期间/授权/故障/并发验收，仅针对自建QA单据。可删除自由草稿采用物理删除并保留历史；无回收站或恢复功能。期间、发票引用和坏状态SQL夹具不代表这些模块的完整业务验收。

浏览器运行该脚本 `prepare`，按输出前缀查询A/B/C/D：A单行删除，B已核对应拒绝，运行 `verify-single`；选C/D实际批量删除，再运行 `verify-batch`。SQL独立核对历史保留、主从记录、被拒绝的B及库存资金不变量。私有夹具、token、报告与截图不发布，不能用于正常业务库。

## 采购订单草稿新增

运行 `python qa/booking_draft_acceptance.py run` 执行9项真实HTTP/MySQL事务、权限、金额、精度、重复并发及失败回滚专项。只允许已绑定的专用QA数据库和服务，不在正常业务库运行。商品/仓库/供应商/人员为本次新建SQL资料夹具，功能授权使用真实新用户OAuth登录并恢复QA Redis原键；资料夹具不证明资料管理完整生命周期已验收。

该脚本prepare/verify保留早期整单录入的历史验收夹具；现行浏览器验收请使用purchase_split_acceptance.py的prepare/verify，不再按旧页面步骤操作。原/add接口的9项回归仍有效，夹具通过真实维护接口建立供货关系后再新增订单。私有会话、资料标识、报告和截图不发布；不代表订单修改/审核/生成采购单、附件上传和所有商品单位组合完成。

## 完整普通采购开单

`python qa/purchase_entry_acceptance.py run` 执行4项实际服务端金额/精度/历史提示/非法输入专项。浏览器运行 `prepare`，按打印的名称在采购单选择实际供应商/商品/仓库，编号用打印值、数量2、税率13，保存后运行 `verify`。从跳转后的列表打开详情改数量3保存后执行 `verify-edited`，核对审核后执行 `verify-audited`，独立核对真实库存与应付。

再运行 `prepare-multi`，回采购单页确认内容空白及新编号，按打印编号多选两种商品、各数量1/税率13、批量选择仓库，保存后运行 `verify-multi`。它核对两条真实明细和175/197.75，并确保前一张已审核库存/应付未变。此流程不证明所有SKU、批次、多单位选择器和附件真实上传；私有会话、夹具、截图、数据库结果不发布。
