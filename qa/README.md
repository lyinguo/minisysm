# 系统业务验收

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

运行 `python qa/purchase_posting_acceptance.py check` 验证核对事务、真实存储故障回滚/重试、组织与角色授权。`posting` 验证实际入库、应付、部分付款和反审核；当前4项仍失败，非零退出必须保留为未完成证据。默认 `all` 执行全部，不能只运行check便宣称采购审核通过。

沿用采购页面专项的数量3草稿，在真实浏览器点击核对后运行 `verify-checked`，点击反核对后运行 `verify-unchecked`，独立验证状态及库存资金不变量。正常业务环境不运行任何这些写入测试。
