/*
 Copyright Zero One Star. All rights reserved.

 @Author: waterox
 @Date: 2022/12/03 14:58:34

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

	  https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/
#include "ApiHelper.h"
#include "stdafx.h"
#include "Router.h"
#include "sales_order_tracking_report/SalesOrderTrackingReportController.h"
#include "other_income_expense_details_report/OtherIncomeExpenseDetailsReportController.h"
#include "sales_summary_report/SalesSummaryReportController.h"
#include "ApiHelper.h"
#include "income_statement/IncomeStatementController.h"
#include "sales_income_statement/SalesIncomeStatementController.h"
#include "controller/product_inventory_transactions_report/ProductInventoryTransactionsReportController.h"
#include "controller/purchase_payments_report/PurchasePaymentsReportController.h"
#include"AccountController/AccountController.h"
#include"Account_PController/Account_PartnersController.h"
#include "controller/cash_bank_list/CashBankListController.h"
#include "controller/procurement_summary_list/ProcurementSummaryListController.h"
#include "controller/procurement_ranking_report/ProcurementRankingReportController.h"
#include "controller/procurement_order_tracking/ProcurementOrderTrackingController.h"
#include "procurement_detail_report/ProcurementDetailReportController.h"
#include "customer_statement/Cus_StateController.h"
#include "sale_detail/Sale_DetailController.h"
#include "goods_summary_report/GoodsSummaryReport.h"
#include "sales_ranking_table/SalesRankingReport.h"
#include "sales_order_tracking_report/SalesOrderTrackingReportController.h"
#include "sales_receipts_table/SalesReceiptsTableController.h"
#include "supplier_statement/SupplierStatementController.h"
#include "ApiHelper.h"
#include "account_payable_aging_report/AccountPayableAgingReportController.h"
#include "inventory_balance_report/InventoryBalanceReportController.h"

// ��������˹ر�Swagger�ĵ���
#ifdef CLOSE_SWAGGER_DOC
// �򻯰󶨿������궨��
#define ROUTER_SIMPLE_BIND(__CLASS__) \
router->addController(__CLASS__::createShared())
#else
// �򻯰󶨿������궨��
#define ROUTER_SIMPLE_BIND(__CLASS__) \
BIND_CONTROLLER(docEndpoints, router, __CLASS__)
#endif


Router::Router(Endpoints* docEndpoints, HttpRouter* router)
{
	this->docEndpoints = docEndpoints;
	this->router = router;
}


void Router::initRouter()
{
	 
	//采购明细表
	ROUTER_SIMPLE_BIND(ProcurementDetailReportController);
	//客户对账单
	ROUTER_SIMPLE_BIND(Cus_StateController);
	//销售订单跟踪表
	ROUTER_SIMPLE_BIND(SalesOrderTrackingReportController);
	//销售明细单
	ROUTER_SIMPLE_BIND(Sale_DetailController);
	//销售排行表
	ROUTER_SIMPLE_BIND(SalesRankingReport);
	//商品收发汇总
	ROUTER_SIMPLE_BIND(GoodsSummaryReport);
	//采购排行表
	ROUTER_SIMPLE_BIND(ProcurementRankingReportController);
	//采购订单跟踪表
	ROUTER_SIMPLE_BIND(ProcurementOrderTrackingController);
	//销售订单汇总表
	ROUTER_SIMPLE_BIND(SalesSummaryReportController);
	//其他收入支出明细表
	ROUTER_SIMPLE_BIND(OtherIncomeExpenseDetailsReportController);
	//应付款明细报表
	ROUTER_SIMPLE_BIND(AccountPayableAgingReportController);
	//库存余额表
	ROUTER_SIMPLE_BIND(InventoryBalanceReportController);
	//商品收发明细表
	ROUTER_SIMPLE_BIND(PurchasePaymentsReportController);
	//采购付款表
	ROUTER_SIMPLE_BIND(ProductInventoryTransactionsReportController);
	//现金银行报表
	ROUTER_SIMPLE_BIND(CashBankListController);
	//采购汇总表
	ROUTER_SIMPLE_BIND(ProcurementSummaryListController);
	//销售收款表
	ROUTER_SIMPLE_BIND(SalesReceiptsTableController);
	//供应商对账单
	ROUTER_SIMPLE_BIND(SupplierStatementController);
	//应收款明细表
	ROUTER_SIMPLE_BIND(AccountController);
	//往来单位欠款表
	ROUTER_SIMPLE_BIND(Account_PartnersController);

	ROUTER_SIMPLE_BIND(IncomeStatementController);
	ROUTER_SIMPLE_BIND(SalesIncomeStatementController);
}
