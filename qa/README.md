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
