#pragma once
#ifndef _COST_INFO_DO_
#define _COST_INFO_DO_
#include "../DoInclude.h"

/**
 * 单据费用详情对象
 */
class CostInfoDO : public BaseDO
{
	// ID
	MYSQL_SYNTHESIZE(string, id, Id);
	// 所属ID
	MYSQL_SYNTHESIZE(string, pid, Pid);
	// 所属支出
	MYSQL_SYNTHESIZE(string, oce, Oce);
	// 单据时间
	MYSQL_SYNTHESIZE(string, time, Time);
	// 结算金额
	MYSQL_SYNTHESIZE(double, money, Money);
public:
	CostInfoDO() : BaseDO("cost_info")
	{
		MYSQL_ADD_FIELD_PK("id", "s", id);
		MYSQL_ADD_FIELD("pid", "s", pid);
		MYSQL_ADD_FIELD("oce", "s", oce);
		MYSQL_ADD_FIELD("time", "s", time);
		MYSQL_ADD_FIELD("money", "d", money);
	}
};
// 为CustomerDO对象指针设定一个别名，使用
typedef std::shared_ptr<CostInfoDO> PtrCostInfoDO;
#endif 