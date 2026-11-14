#pragma once
#ifndef _GOODS_SUMMARY_REPORT_VIEW_DO_H
#define _GOODS_SUMMARY_REPORT_VIEW_DO_H

#include "../DoInclude.h"

/**
 * 商品收发汇总表数据DO类
 * 需要数据库原始表goods,warehouse, buy_info, bre_info,
					sor_info, sre_info, extry_info, entry_info,
					swap_info, room, room_info
 */
class GoodsSummaryReportViewDO : public BaseDO
{
	// 商品名称
	MYSQL_SYNTHESIZE(std::string, name, Name);

	// 仓库名称
	MYSQL_SYNTHESIZE(std::string, warehouse, Warehouse);

	// 商品编号
	MYSQL_SYNTHESIZE(std::string, number, Number);

	// 商品规格型号
	MYSQL_SYNTHESIZE(std::string, spec, Spec);

	// 单位
	MYSQL_SYNTHESIZE(std::string, unit, Unit);

	// 汇总 - 单位成本
	MYSQL_SYNTHESIZE(double, sumUct, SumUct);

	// 汇总 - 数量
	MYSQL_SYNTHESIZE(int64_t, sumUns, SumUns);

	// 汇总 - 成本总额
	MYSQL_SYNTHESIZE(double, sumBct, SumBct);

	// 期初 - 单位成本
	MYSQL_SYNTHESIZE(double, stateUct, StateUct);

	// 期初 - 数量
	MYSQL_SYNTHESIZE(int64_t, stateUns, StateUns);

	// 期初 - 成本总额
	MYSQL_SYNTHESIZE(double, stateBct, StateBct);

	// 采购单 - 单位成本
	MYSQL_SYNTHESIZE(double, buyUct, BuyUct);

	// 采购单 - 数量
	MYSQL_SYNTHESIZE(int64_t, buyUns, BuyUns);

	// 采购单 - 成本总额
	MYSQL_SYNTHESIZE(double, buyBct, BuyBct);

	// 采购退货单 - 单位成本
	MYSQL_SYNTHESIZE(double, breUct, BreUct);

	// 采购退货单 - 数量
	MYSQL_SYNTHESIZE(int64_t, breUns, BreUns);

	// 采购退货单 - 成本总额
	MYSQL_SYNTHESIZE(double, breBct, BreBct);

	// 销售单 - 单位成本
	MYSQL_SYNTHESIZE(double, sellUct, SellUct);

	// 销售单 - 数量
	MYSQL_SYNTHESIZE(int64_t, sellUns, SellUns);

	// 销售单 - 成本总额
	MYSQL_SYNTHESIZE(double, sellBct, SellBct);

	// 销售退货单 - 单位成本
	MYSQL_SYNTHESIZE(double, sreUct, SreUct);

	// 销售退货单 - 数量
	MYSQL_SYNTHESIZE(int64_t, sreUns, SreUns);

	// 销售退货单 - 成本总额
	MYSQL_SYNTHESIZE(double, sreBct, SreBct);

	// 调拨单-出 - 单位成本
	MYSQL_SYNTHESIZE(double, swapOutUct, SwapOutUct);

	// 调拨单-出 - 数量
	MYSQL_SYNTHESIZE(int64_t, swapOutUns, SwapOutUns);

	// 调拨单-出 - 成本总额
	MYSQL_SYNTHESIZE(double, swapOutBct, SwapOutBct);

	// 调拨单-入 - 单位成本
	MYSQL_SYNTHESIZE(double, swapEnterUct, SwapEnterUct);

	// 调拨单-入 - 数量
	MYSQL_SYNTHESIZE(int64_t, swapEnterUns, SwapEnterUns);

	// 调拨单-入 - 成本总额
	MYSQL_SYNTHESIZE(double, swapEnterBct, SwapEnterBct);

	// 其它入库 - 单位成本
	MYSQL_SYNTHESIZE(double, entryUct, EntryUct);

	// 其它入库 - 数量
	MYSQL_SYNTHESIZE(int64_t, entryUns, EntryUns);

	// 其它入库 - 成本总额
	MYSQL_SYNTHESIZE(double, entryBct, EntryBct);

	// 其它出库 - 单位成本
	MYSQL_SYNTHESIZE(double, extryUct, ExtryUct);

	// 其它出库 - 数量
	MYSQL_SYNTHESIZE(int64_t, extryUns, ExtryUns);

	// 其它出库 - 成本总额
	MYSQL_SYNTHESIZE(double, extryBct, ExtryBct);

public:
	GoodsSummaryReportViewDO() : BaseDO("")  // 使用空表名，因为这是查询结果视图
	{
		// 基本商品信息字段
		MYSQL_ADD_FIELD("name", "s", name);
		MYSQL_ADD_FIELD("warehouse", "s", warehouse);
		MYSQL_ADD_FIELD("number", "s", number);
		MYSQL_ADD_FIELD("spec", "s", spec);
		MYSQL_ADD_FIELD("unit", "s", unit);

		// 汇总数据字段
		MYSQL_ADD_FIELD("sum_uct", "d", sumUct);
		MYSQL_ADD_FIELD("sum_uns", "ll", sumUns);
		MYSQL_ADD_FIELD("sum_bct", "d", sumBct);

		// 期初数据字段
		MYSQL_ADD_FIELD("state_uct", "d", stateUct);
		MYSQL_ADD_FIELD("state_uns", "ll", stateUns);
		MYSQL_ADD_FIELD("state_bct", "d", stateBct);

		// 采购单数据字段
		MYSQL_ADD_FIELD("buy_uct", "d", buyUct);
		MYSQL_ADD_FIELD("buy_uns", "ll", buyUns);
		MYSQL_ADD_FIELD("buy_bct", "d", buyBct);

		// 采购退货单数据字段
		MYSQL_ADD_FIELD("bre_uct", "d", breUct);
		MYSQL_ADD_FIELD("bre_uns", "ll", breUns);
		MYSQL_ADD_FIELD("bre_bct", "d", breBct);

		// 销售单数据字段
		MYSQL_ADD_FIELD("sell_uct", "d", sellUct);
		MYSQL_ADD_FIELD("sell_uns", "ll", sellUns);
		MYSQL_ADD_FIELD("sell_bct", "d", sellBct);

		// 销售退货单数据字段
		MYSQL_ADD_FIELD("sre_uct", "d", sreUct);
		MYSQL_ADD_FIELD("sre_uns", "ll", sreUns);
		MYSQL_ADD_FIELD("sre_bct", "d", sreBct);

		// 调拨单-出数据字段
		MYSQL_ADD_FIELD("swap_out_uct", "d", swapOutUct);
		MYSQL_ADD_FIELD("swap_out_uns", "ll", swapOutUns);
		MYSQL_ADD_FIELD("swap_out_bct", "d", swapOutBct);

		// 调拨单-入数据字段
		MYSQL_ADD_FIELD("swap_enter_uct", "d", swapEnterUct);
		MYSQL_ADD_FIELD("swap_enter_uns", "ll", swapEnterUns);
		MYSQL_ADD_FIELD("swap_enter_bct", "d", swapEnterBct);

		// 其它入库数据字段
		MYSQL_ADD_FIELD("entry_uct", "d", entryUct);
		MYSQL_ADD_FIELD("entry_uns", "ll", entryUns);
		MYSQL_ADD_FIELD("entry_bct", "d", entryBct);

		// 其它出库数据字段
		MYSQL_ADD_FIELD("extry_uct", "d", extryUct);
		MYSQL_ADD_FIELD("extry_uns", "ll", extryUns);
		MYSQL_ADD_FIELD("extry_bct", "d", extryBct);
	}
};
using PtrGoodSummaryReportViewDO = std::shared_ptr<GoodsSummaryReportViewDO>;

#endif // !_GOODS_SUMMARY_REPORT_VIEW_DO_H