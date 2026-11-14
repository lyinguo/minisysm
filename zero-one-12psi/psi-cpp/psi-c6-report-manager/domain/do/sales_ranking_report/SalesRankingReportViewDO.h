#pragma once
#ifndef _SALES_RANKING_REPORT_VIEW_DO_H
#define _SALES_RANKING_REPORT_VIEW_DO_H

#include "../DoInclude.h"

/*
需要的数据库原始表sor_info, goods。
*/
class SalesRankingReportViewDO : public BaseDO
{
	// 商品名称
	MYSQL_SYNTHESIZE(std::string, name, Name);

	// 商品编号
	MYSQL_SYNTHESIZE(std::string, number, Number);

	// 规格型号
	MYSQL_SYNTHESIZE(std::string, spec, Spec);

	// 属性
	MYSQL_SYNTHESIZE(std::string, attr, Attr);

	// 单位
	MYSQL_SYNTHESIZE(std::string, unit, Unit);

	// 数量
	MYSQL_SYNTHESIZE(double, nums, Nums);

	// 折扣
	MYSQL_SYNTHESIZE(double, dsc, Dsc);

	// 税额
	MYSQL_SYNTHESIZE(double, tat, Tat);

	// 价税总和
	MYSQL_SYNTHESIZE(double, tpt, Tpt);

	// 成本总额
	MYSQL_SYNTHESIZE(double, bct, Bct);

	// 单位成本
	MYSQL_SYNTHESIZE(double, uct, Uct);

	// 商品利润
	MYSQL_SYNTHESIZE(double, gpt, Gpt);

	// 商品利润率
	MYSQL_SYNTHESIZE(std::string, gpr, Gpr);

public:
	SalesRankingReportViewDO() : BaseDO("")  // 使用空表名，因为这是查询结果视图
	{
		// 添加所有字段映射
		MYSQL_ADD_FIELD("name", "s", name);
		MYSQL_ADD_FIELD("number", "s", number);
		MYSQL_ADD_FIELD("spec", "s", spec);
		MYSQL_ADD_FIELD("attr", "s", attr);
		MYSQL_ADD_FIELD("unit", "s", unit);
		MYSQL_ADD_FIELD("nums", "d", nums);
		MYSQL_ADD_FIELD("dsc", "d", dsc);
		MYSQL_ADD_FIELD("tat", "d", tat);
		MYSQL_ADD_FIELD("tpt", "d", tpt);
		MYSQL_ADD_FIELD("bct", "d", bct);
		MYSQL_ADD_FIELD("uct", "d", uct);
		MYSQL_ADD_FIELD("gpt", "d", gpt);
		MYSQL_ADD_FIELD("gpr", "s", gpr);
	}
};

using PtrSalesRankingReportViewDO =std::shared_ptr<SalesRankingReportViewDO>;

#endif // !_SALES_RANKING_REPORT_VIEW_DO_H
