# 库存与销售管理系统

在 zero-one-psi 项目基础上维护的进销存系统，包含 Java 后端、Vue 前端和 C++ 服务源码。保留原项目 Apache-2.0 许可证及源码中的作者声明。

## 目录

- `zero-one-12psi/psi-frontend`：Vue 3、TypeScript、Element Plus 前端。
- `zero-one-12psi/psi-java`：Spring Boot、Spring Cloud Alibaba 后端及测试。
- `zero-one-12psi/psi-cpp`：C++ 业务服务及自有公共组件。
- `database/schema.sql`：仅数据库结构，不含账户、密码或业务记录。
- `database/migrations`：跨服务关联约束迁移，首次启动前必须安装。
- [系统检查与修复清单](SYSTEM-AUDIT.md)：已修复问题、删除策略和尚未实现的能力。
- `config/nacos/*.example`：脱敏的配置模板。
- `scripts`：前端检查、仓库事务测试及只读接口检查。

## 本地配置

1. 准备 JDK 8、Maven、Node.js、pnpm、MySQL、Redis、Nacos。
2. 使用 `database/schema.sql` 建表；在本地初始化自己的角色、管理员及业务基础资料。本仓库不提供真实数据库备份或预置账户密码。
3. 将 `config/nacos/*.example` 按需复制为本地配置，配置模板中列出的环境变量，并将配置导入 Nacos。数据库、短信、邮箱、文件存储等凭据必须自行设置。
4. 为 OAuth2 生成并在本地配置签名密钥。本仓库不包含部署私钥、证书库或现有环境的密钥文件。
5. 将 `zero-one-12psi/psi-java/settings.xml.example` 复制为 `settings.xml`，按需配置依赖源；依赖源凭据只存放在本地。
6. 将 `zero-one-12psi/psi-frontend/.env.example` 复制为 `.env.development`，然后在前端目录执行：

   ```sh
   pnpm install --frozen-lockfile
   pnpm dev
   ```

   默认前端端口为 3000，API 代理目标为本地 10001 网关。后端各模块须先连接已配置的 Nacos、数据库及 Redis，再依次启动认证、登录、网关和业务服务。

C++ 服务所需的第三方 SDK、头文件和预编译库不随源码上传，请按 CMake 的依赖声明在本地准备。关闭服务所用的 `PSI_STOP_PASSWORD` 通过本地环境变量设置。

## 检查

在 Windows PowerShell 中执行：

```powershell
./scripts/check-frontend.ps1 -Build
./scripts/check-warehouse.ps1
./scripts/check-basic.ps1
python scripts/lib/master-integrity.py test
```

检查脚本中的 JDK、Maven 路径可按本机安装位置调整。仓库后端测试使用独立 H2 测试库，不操作现有业务数据。

运行 `scripts/lib/check-readonly-apis.ps1` 前，在本地设置 `PSI_USERNAME`、`PSI_PASSWORD`；此脚本只调用查询接口。

## 本次维护

- 修复报表页面渲染异常、路由切换、登录凭证失效处理及 Excel 导出。
- 补齐供应商模板下载、采购订单删除、客户选择和操作日志用户查询。
- 仓库报表读取真实单据，支持现有明细保存、审核和反审核；加入版本校验、库存不足保护、事务回滚、重复审核保护，以及批次和序列号校验。
- 增加主资料删除、余额、层级、制单用户引用及管理员保护；菜单改为拒绝隐式级联删除。
- 客户、供应商、仓库支持真实批量导入；商品上传接入真实接口，修复账户编辑重置余额和资金选择器误用编号的问题。
- 未统一接入业务的功能参数暂只读，详见系统检查清单。验证范围包括前端路由、隔离事务、MySQL 关联及并发、实际只读接口。

## 安装关联保护

准备 Python 3 和 Docker，在业务服务停止时执行：

```powershell
python scripts/lib/master-integrity.py install --database zo_psi
```

默认使用 `mysql8` 容器，在容器内部读取已有数据库凭据。可用 `--container`、`--database` 指定本机环境。不要把密码或真实数据提交到仓库。

迁移增加 121 个触发器及组织、菜单父级外键，保留历史记录；有业务引用或余额的资料不能直接删除。历史重复编号、孤立关联不会自动合并或删除，可运行 `python scripts/lib/master-integrity.py audit` 查看异常数量。部署时不能遗漏迁移。

## 发布范围

本仓库是源码和配置模板副本，未上传本地运行凭据、实际密钥、环境文件、数据库记录、日志、缓存、安装包、构建产物、第三方预编译依赖或单个超过 5 MiB 的文件。首次运行需要完成上述本地配置。
