# 系统业务验收

## 销售单核对与审核的读取版本

运行`python qa/sale_snapshot_acceptance.py run`执行16项真实HTTP/MySQL专项，包含旧版本、版本格式、旧数组入口、历史故障、批量库存资金回滚、并发和列表读取竞争；只有`baseline`则执行前6项。所有命令仅针对专用QA环境；必须与其他期间、角色和读取门控夹具串行执行。原有销售业务专项会在命令前显式读取版本，不能作为旧页面安全性的替代证明。

销售核对与审核保留`check?check=true|false`、`examine?examine=true|false`路径，JSON正文改为`{ "ids": ["所读ID"], "version": "所读64位小写SHA256" }`；批量使用`versions`映射完整覆盖IDs，不与version混用。列表行和完整详情返回同一种版本。版本失效后需要重新打开并核对实际内容，不能独立取新版本替旧页面授权。

浏览器运行`python qa/sale_browser_acceptance.py prepare`，使用18030的隔离会话进入`/sales-order-report`，筛选打印编号，实际核对和审核后执行`verify-audited`；页面反审核后执行`verify-reversed`，反核对后执行`verify-unchecked`。独立验证库存、现金、应收、流水、状态及3/4/5条当前操作人历史。SQL夹具、会话、截图及日志只保留于私有runtime/reports，不发布；这些检查不代表销售退货或全部角色页面已验收。

## 采购收货单真实附件

`python qa/purchase_attachment_acceptance.py run`执行17项真实HTTP multipart/二进制下载、MySQL、OAuth权限与库存资金专项，只允许专用QA数据库和18023端口；与其他有期间/授权夹具的验收串行执行。

新建采购单先保存草稿，再从采购单报表打开详情，在底部“采购单附件”选择文件。上传、移除立即保存，不必再次保存采购单。每单最多10个有效附件，单文件1字节至5MiB；同名同内容可在当前版本安全重试，同名不同内容先移除再上传。核对前须保存其他编辑；有未保存内容、已核对/审核/核销、已结账或存在真实下游凭据时不能修改附件，具备详情权限且组织允许时仍可下载。反审核、反核对并满足业务规则后才能再改附件。

附件字节、SHA256、操作人与日志同事务落到MySQL；不使用公开静态URL，下载以附件方式返回application/octet-stream并校验内容。移除为逻辑移除，界面不再提供下载，保留原字节与移除人；无关联自由草稿允许物理删除时，外键同步清理有效及已移除附件，独立操作历史保留。历史buy.file仅保留并显示未迁移提示，不自动请求任意历史URL。只有两个采购模块接入了真实服务，其余共享旧上传模块继续待验收。另运行`python qa/backup_acceptance.py run`，备份专项会实际上传两类附件并在独立临时QA库恢复，核对两表全部元数据、实际字节摘要和移除标记。

文件元数据（包含移除状态）参与详情、修改、核对与审核共用版本，列表采用同一RR快照内的四次批量元数据读取；旧窗口不能审核或保存新文件之前的内容。返回上传时间戳并以明确的北京时间显示，原数据库日期不回写；旧服务缺少时间戳时明确标注服务器时间。上传中禁止关闭、保存或核对。新建页原/api/upload占位入口已替换为保存后上传的操作指引。

浏览器运行`prepare`，在18030隔离会话按打印编号打开采购单，只上传生成的`qa/runtime/QA purchase receipt attachment.txt`。执行`uploaded`核对SQL；关闭重开并下载，再用`uploaded --download <实际文件绝对路径>`核对SHA256。核对、审核后执行`posted`，此时应库存2/现金50/应付176，上传及移除禁用，下载仍可用；下载后也可用`posted --download <实际路径>`核对文件。反审核、反核对后移除，关闭重开应无下载，执行`removed`核对逻辑标记、原字节/操作人、累计历史7条及0/100/0恢复。私有会话、数据库记录、日志、截图、下载和二进制不发布。

## 采购收货单核对与审核的读取版本

`python qa/purchase_snapshot_acceptance.py run`执行11项真实HTTP/MySQL专项。详情GET `/purchase-note/document/{id}`与列表GET `/purchase-note/list`返回同一SHA256版本。POST `/purchase-note/verification`、`/purchase-note/audit`必须提交单单`{ids:[id],type:0或1,version:读取版本}`，或完整批量`{ids:[...],type:0或1,versions:{每个ID:读取版本}}`；禁止无版本、混用、缺失或额外成员。前后端须同时更新，旧脚本必须先明确读取版本再提交，不能在审核API内部自动取新版本替旧页面授权。

每次修改、核对/反核对、审核/反审核均使旧页面失效；重新读取后提交相同目标仍不重复入账。同一旧版本并发只允许一次状态变更，其他请求被明确拒绝。列表头、明细与操作记录的版本通过四次批量查询计算（含附件元数据），沿用同一REPEATABLE_READ快照；功能授权及组织范围仍由当前账号/角色单独判断。版本不是授权凭据。采购正反入账仍按原凭据校验和实际库存资金事务执行。

详情有未保存字段时先保存；确认框打开后继续编辑也会阻止提交。旧页面被拒绝后不自动刷新版本或丢失输入，关闭重开并核对最新内容再操作。批量保留全部选中ID及版本，任一失败整批回滚；不丢弃缺ID成员后仅提交余下单据。错误保留选择，成功提交与刷新失败分开提示。

浏览器运行`prepare`创建A/B/C三张专用采购单。在18030隔离页面按打印编号打开A，备注改为`QA local unsaved`后点核对应阻止，运行`verify-dirty`。关闭重开A，执行`external-edit`实际更新，再从旧窗口核对应拒绝，运行`verify-stale`；关闭重开确认`QA external detail newer`，核对后运行`verify-checked`。审核、反审核、反核对后分别运行`verify-audited`、`verify-reversed`、`verify-unchecked`。每步独立核对三单状态历史及实际库存/现金/应付。

列表查询打印前缀，仅选B/C，执行`external-batch`更新C。旧列表批量核对应整批拒绝且保留选择，运行`verify-batch-stale`；刷新后核对最新C备注，重新选B/C核对，运行`verify-batch-checked`。A始终不参与该批。脚本的读取竞争检查使用同一QA本地调度门闩，新增固定purchase模式只暂停PurchaseSnapshotService.versions入口，最长15秒，finally恢复原类；仅SQL改变本次夹具，不替换查询结果。所有期间及授权测试串行，浏览器列表请求不得与读取门闩并行。私有token/报告/截图/夹具不推送。收货单附件仍未实现，本节不把占位上传算作完成。

## 采购订单真实附件

`python qa/booking_attachment_acceptance.py run` 执行14项真实HTTP multipart/二进制下载、OAuth角色及独立MySQL验收。仅使用专用QA库和18023端口，必须与其他业务验收串行运行：关闭期间及Redis授权夹具会暂时改变该QA环境的共享条件，不能并行计数。

从采购订单报表打开已保存的未审核订单，在“订单附件”选择文件。每个附件1字节至5MiB，每单最多10个有效附件；同名同内容可安全重试，同名不同内容须先移除旧文件。上传和移除立即保存，不必再点击订单保存。改过订单字段时先保存并重新打开；已审核、接收、关闭、关联采购或结账订单拒绝附件变更。下载需要订单详情权限，上传和移除同时需要详情与修改权限，按当前数据库角色/组织及QA Redis授权校验。

二进制、SHA256和元数据存于MySQL，与操作历史和订单版本同事务提交；下载校验原字节，使用Content-Disposition: attachment及application/octet-stream且不提供公开静态URL。移除为逻辑移除，界面不能再下载，后台保留字节和操作人；允许删除的无关联未执行草稿仍是物理删除，外键同步清理其附件，独立操作记录保留。历史bor.file字段不会被自动访问或声称迁移完成。

浏览器验收运行`prepare`，在18030隔离会话按打印单号打开详情，只上传脚本生成的`qa/runtime/QA attachment browser.txt`。运行`uploaded`核对SQL，关闭重开后下载，再执行`uploaded --download <实际下载绝对路径>`核对精确SHA256；移除并关闭重开后运行`removed`。测试文件、会话、报告、下载和截图都不发布。该范围仅采购订单附件，不代表采购收货/销售/退货等共享旧上传入口完成，也不代表网关全部角色路径已验收。


## 采购订单列表快照与整批审核

`python qa/booking_batch_audit_acceptance.py run`执行10项真实列表版本、陈旧成员整批回滚、完整选择、实际缺失成员、存储故障重试、重叠并发、当前权限/组织/撤权、审核反审核旧快照及并发列表读取检查。列表每行返回version；多单审核必须提交`{ids,type,versions:{订单ID:读取版本}}`，单单详情仍可提交version。不可省略版本，也不能混用两种模式；任何选中成员缺失、过期或不符合业务规则，整批不提交。页面缺ID/版本、重复项或混合审核状态直接整批拒绝，失败保留选择，刷新后核对并重新选择。每页版本通过四次批量读取计算（含附件元数据），不逐行查库。

运行`prepare`建立3张专用订单，在18030页面按打印前缀查询，仅勾选打印的两张。保持旧列表执行`external-edit`修改第二张，再点“操作→审核”，应显示“本次整批未处理”，执行`verify-stale`。刷新当前筛选，重新勾选两张审核，执行`verify-approved`；全选三张点反审核，应整批拒绝，执行`verify-mixed`；取消第三张选择，再反审核，执行`verify-reversed`。四个检查点核对全部三单状态/历史、第二单新备注和未选第三单不变，以及库存/应付0、现金100。

`read-race`要求Windows本地JDK8：read_gate.py会编译随附Java源文件，核对专用QA进程的路径、端口和应用名后，通过同用户Attach API只在列表页读取后的入口增加一次最长15秒的调度停顿，不替换查询或业务值，也不开放调试网络端口。观察实际请求已停住后，仅SQL修改本次自建明细，再继续请求验证旧快照与后续新版本；finally恢复原类。助手同样拒绝正常服务进程。源码可发布，生成的JAR、class、标记和日志只在私有runtime；不能在正常服务执行该测试。

## 采购订单并发修改与详情审核版本

`python qa/booking_conflict_acceptance.py run`执行8项真实HTTP/OAuth/MySQL专项：稳定版本、过期编辑、同版本并发仅一成功、带版本详情审核及反审核、禁止省略/伪造版本、实际存储故障回滚重试、资料改名不误报冲突及当前角色/组织/撤权保护。修改接口必须先读取`GET /purchase-order/document?id=...`的顶层version并在PUT /purchase-order/update提交；审核详情可携带单据version，审核后从status读取新版本用于下一次操作。版本由真实单据、明细及操作记录计算，不是授权凭据，仍需原资源权限和组织归属。无版本的原批量审核仍处理当前单据，其陈旧列表阅读一致性尚未验收。

运行`prepare`后，在18030隔离页面按打印单号打开详情，改备注为`QA local unsaved`，点击审核应阻止，执行`verify-dirty`；保存后执行`verify-saved`。重新打开并确认该备注，再执行`external-edit`模拟另一真实请求更新。在旧窗口审核应提示重新打开，执行`verify-stale-audit`；改备注为`QA local preserved`并保存也应拒绝，窗口和输入保留，执行`verify-stale-save`。关闭重新打开后必须看到`QA external newer`，人工核对改为`QA resolved after review`并保存，执行`verify-resolved`。重新打开审核、同窗口反审核，分别执行`verify-approved`、`verify-reversed`；操作记录应累计到6，库存/应付0、现金100。失败不自动覆盖或合并他人修改；关闭窗口后的自动恢复/合并、批量审核快照和附件冲突仍待验收。

## 采购订单详情修改与真实名称

`python qa/booking_detail_acceptance.py run`执行真实详情资料名称、四位折扣/税额修改及审核、可选人员/物流三项专项。新增与修改的人员均可留空；填写时保留实际ID并继续校验归属。详情补充真实名称，页面修改保留原折扣、税额及已有附件字段，未税/含税合计分别由明细计算。减免20表示扣减20%，不是支付20%。空物流不能被写成“自动识别”。已审核详情只读，返回未审核需先按业务规则反审核。

运行`prepare`创建专用订单，再在18030隔离页面按打印单号筛选、打开详情。原单价1.0001、数量0.5、减免10%、税率13%；修改减免为20，失焦后应为未税0.4001、税额0.052、含税0.4521。点击订单底部保存，运行`verify-saved`独立核对SQL；重新打开并审核，运行`verify-approved`核对真实状态、操作历史及库存/应付不变。此过程仅普通商品场景，不证明附件上传、全部编辑冲突或未保存内容审核等交互全部完成。会话和夹具仅私有runtime/reports。

## 采购订单列表名称、日期与筛选

`python qa/booking_list_acceptance.py baseline`重现最初4项失败，`run`执行8项真实HTTP/OAuth/MySQL专项。保留原ID并补充实际名称、日期和明确状态；异常枚举显示异常。供应商/人员/制单人支持ID或名称，商品名称及备注可过滤；状态传0起真实值并兼容旧中文。严格日期、范围及分页校验，同日期按ID稳定排序，金额明确标注为本页合计。

隔离浏览器审核第二张夹具订单，已审核仅1条；反审核后已审核0条、未审核3条。分别执行`python qa/booking_browser_acceptance.py verify-list-approved`与`verify-list-reversed`独立核对状态、历史及库存/应付不变。旧孤儿资料名称分支尚无真实验证；详情人员ID及其他选择器体验继续待修复，不代表订单模块或全系统完成。

## 采购订单页面实际上传下载

运行`python qa/booking_browser_acceptance.py prepare`新建专用账号、供货资料和有效/独立错误单号的XLSX，`verify-session`核验真实QA用户服务接受有效令牌、拒绝伪造签名和空令牌。启动`vite.qa.config.ts`的18030本机服务，打开`http://127.0.0.1:18030/qa-browser-login`并点击进入采购订单验收。此入口使用实际OAuth签发的QA会话，当前用户经18091验证；菜单留空，不代表菜单或生产登录流程验收。生产配置没有这个入口。

在`/purchase-booking-report`的“批量”中实际下载模板，先上传`qa/runtime/order-browser-invalid.xlsx`，页面应显示第4行错误，执行`verify-rejected`；上传valid文件，执行`verify-saved`。按打印单号筛选、勾选订单并实际下载简单及详细报表，将下载的模板/简单/详细文件分别复制为`qa/runtime/browser-template.xlsx`、`browser-export-simple.xlsx`、`browser-export-detail.xlsx`，执行`verify-files`独立核对XLSX内容及SQL。

执行`prepare-extra`生成second/third文件。页面上传second，按原单号前缀筛选为2条；保留该筛选上传third后仍只显示3条。仅勾选原单和second，实际下载两个报表，复制为`browser-export-multi-simple.xlsx`和`browser-export-multi-detail.xlsx`，运行`verify-multi-files`，应仅含2单4明细、540/610.2，不能含未勾选third。会话、资料ID、XLSX、截图和数据库结果都只在私有runtime/reports，不发布。上述普通商品场景已实际操作通过；不能外推到所有资料组合及全系统。

## 采购订单Excel导出

`python qa/booking_export_acceptance.py baseline`执行最初5项基线检查，`run`执行9项真实HTTP/XLSX内容、精度、权限/当前组织、选择完整性、全部选中订单合计、异常状态和文本单元格及只读不变量验收。仅导出本次新建的专用QA订单，数据和下载文件不得发布。

简单报表`GET /purchase-order/export-bor?pid=<逗号分隔ID>`使用同名资源权限，详细报表`POST /purchase-order/export/detail`使用独立详细导出权限，正文为非空不同ID数组，最多200张。任一缺失/无权单据整批拒绝，空ID不能表示全部。详细报表保留原JSON Base64协议，前端解码为真正XLSX后下载；包含“订单汇总”和“商品明细”，汇总每单只计一次，明细保留折扣/税额/实际已收数量。导出不等于可直接导入的模板，导入请另下载专用模板。页面实际点击下载仍须独立浏览器验收，不以API文件内容和组件测试代替。

## 采购订单Excel导入

`python qa/booking_import_acceptance.py baseline`执行最初7项基线保护检查，`run`执行全部15项真实模板下载、XLSX上传、持久化、权限/当前组织、金额/引用/供货/单位、异常文件/行/数量限制/结账期间、第二订单存储故障整批回滚重试、并发及入库反审核链。仅向严格绑定的18023采购服务与专用QA数据库写入。

前端采购订单报表“导入/批量”入口下载`/purchase-order/import/template`服务端模板，先看“填写说明”，第3行开始填资料编号；同订单后续商品可留空前9列，每张订单向一家供应商采购，另家供应商填写另一个单号。折扣为减免百分比，自动金额留空，不覆盖已有单号。新订单仅为未审核草稿；订单审核后生成收货采购单，再核对审核才入库。测试的关闭期间由SQL夹具设置并清理，资料由专用夹具及供货维护接口准备，不证明期间/全部资料功能完成；本批浏览器停在登录入口，页面文件上传未完成验收，不能用接口测试替代。

## 从采购订单生成收货草稿

`python qa/booking_receive_acceptance.py run` 执行23项实际订单预览/生成、数量占用、来源权限、部分收货库存应付、故障回滚/重试、并发、版本修改/删除释放及关闭/异常状态保护专项；baseline保留初始3项失败复现。`source-state`单独执行新增8项异常审核/执行枚举、生成/直接新增/入库/反审核及订单审核保护。preview-race独立用真实存储延迟触发器协调并观察并发事务，验证等待生成提交后可用数量和已生成草稿链接均为当前数据；不能在正常业务库运行。所有写入限定严格QA库和18023服务，角色键、期间和触发器只清理/恢复本次夹具。关闭和异常枚举只修改本次QA来源夹具；验证多值状态不因驱动布尔映射而放行，不代表关闭/重开整个功能完成。

浏览器执行prepare，按打印编号进入隔离采购订单报表，详情“生成→采购单”打开两行收货预览，核对数量各2、单价100、折扣10%、税率13%，生成后执行verify-generated。跳转采购单报表后打开详情，核对再审核，执行verify-posted；页面反审核后执行verify-reversed。独立校验真实来源ID、两行金额360/406.8、实际库存0→4→0、应付0→406.8→0和订单已收0→4→0，现金始终100。返回来源订单再次预览，应显示原草稿占用、可生成0、生成按钮禁用，可点击原采购单编号继续处理。私有资料、会话、截图和结果不发布。

新GET /purchase-order/receive-preview与POST /purchase-order/receive使用/purchase-order/generate-purchaseData资源，生成还要求/purchase-note/add。旧单行generate-purchaseData查询修正为订单表并返回剩余量，多行会提示使用完整收货预览，不能静默只取首行。已有未入库草稿占用数量不是实际库存；必须核对审核后才入库，反审核回到草稿仍保留占用。批次/序列/全部多单位录入和整个系统继续待验收。

## 采购订单审核及实际订单到入库

`python qa/booking_audit_acceptance.py run` 执行12项真实UUID审核、整批失败/故障回滚、并发、当前角色/组织权限、供货状态、金额、期间、完整读取和旧修改保护。联动用真实接口创建订单并审核，再实际创建带来源头/行ID的采购单，核对审核及反审核，独立核对库存/现金/应付/订单已接收量。与其他QA写入测试串行执行，角色键恢复、期间和故障触发器仅清理本次自建夹具。

浏览器运行prepare，在18030隔离工作区进入采购订单报表，按打印编号筛选，详情应完整显示2条商品，点击审核后执行verify-audited，再页面反审核后执行verify-reversed。它核对状态1再0、头400/452和两条明细、库存0/现金100/应付0。新完整读取使用/purchase-order/document，授权资源仍是/purchase-order/detail；审核及状态读取用/purchase-order/audit，列表用/purchase-order/list。无权限不是可用演示数据的理由。此专项不证明页面生成采购单、全部订单修改/导入/删除/导出权限和全系统验收完成。

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

来源订单数值状态专项运行 `python qa/sale_posting_extended.py source-state`，完整扩展命令也包含这5项：关闭来源禁止审核/反审核、异常审核枚举和未知执行状态拒绝、分两次完成实际出库及反审核恢复。订单关闭/异常状态使用仅属本次QA的SQL夹具，出入库、销售保存/核对/审核/反审核使用真实接口并核对库存、现金、应收和已执行量；不代表销售订单关闭/重开页面及完整生命周期已验收。

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

## 采购订单删除

运行 `python qa/booking_delete_acceptance.py baseline` 保留原删除基线保护检查，`run`执行全部11项实际删除、真实下游、批量事务故障、权限及并发验收。仅删除本次新建的专用QA订单。无关联未执行草稿是物理删除，无回收站；操作历史保留。SQL坏状态/旧编号/凭据夹具仅用于保护断言，不证明完整期间/发票业务已验收。该命令依赖18023采购及同一专用库/QA Redis，不能指向正常业务服务。

## 采购订单草稿新增

运行 `python qa/booking_draft_acceptance.py run` 执行9项真实HTTP/MySQL事务、权限、金额、精度、重复并发及失败回滚专项。只允许已绑定的专用QA数据库和服务，不在正常业务库运行。商品/仓库/供应商/人员为本次新建SQL资料夹具，功能授权使用真实新用户OAuth登录并恢复QA Redis原键；资料夹具不证明资料管理完整生命周期已验收。

该脚本prepare/verify保留早期整单录入的历史验收夹具；现行浏览器验收请使用purchase_split_acceptance.py的prepare/verify，不再按旧页面步骤操作。原/add接口的9项回归仍有效，夹具通过真实维护接口建立供货关系后再新增订单。私有会话、资料标识、报告和截图不发布；不代表订单修改/审核/生成采购单、附件上传和所有商品单位组合完成。

## 完整普通采购开单

`python qa/purchase_entry_acceptance.py run` 执行4项实际服务端金额/精度/历史提示/非法输入专项。浏览器运行 `prepare`，按打印的名称在采购单选择实际供应商/商品/仓库，编号用打印值、数量2、税率13，保存后运行 `verify`。从跳转后的列表打开详情改数量3保存后执行 `verify-edited`，核对审核后执行 `verify-audited`，独立核对真实库存与应付。

再运行 `prepare-multi`，回采购单页确认内容空白及新编号，按打印编号多选两种商品、各数量1/税率13、批量选择仓库，保存后运行 `verify-multi`。它核对两条真实明细和175/197.75，并确保前一张已审核库存/应付未变。此流程不证明所有SKU、批次、多单位选择器和附件真实上传；私有会话、夹具、截图、数据库结果不发布。
