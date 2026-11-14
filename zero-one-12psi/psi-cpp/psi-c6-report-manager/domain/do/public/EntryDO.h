#pragma once
#ifndef _ENTRY_DO_
#define _ENTRY_DO_
#include "../DoInclude.h"

/**
 * 其他入库单数据对象
 */
class EntryDO : public BaseDO
{
	// ID
	MYSQL_SYNTHESIZE(string, id, Id);
	// 供应商
	MYSQL_SYNTHESIZE(string, supplier, Supplier);
	// 所属组织
	MYSQL_SYNTHESIZE(string, frame, Frame);
	// 单据时间
	MYSQL_SYNTHESIZE(string, time, Time);
	// 单据编号
	MYSQL_SYNTHESIZE(string, number, Number);
	// 单据类型
	MYSQL_SYNTHESIZE(int, type, Type);
	// 单据成本
	MYSQL_SYNTHESIZE(double, total, Total);
	// 单据费用
	MYSQL_SYNTHESIZE(double, cost, Cost);
	// 关联人员
	MYSQL_SYNTHESIZE(string, people, People);
	// 物流信息
	MYSQL_SYNTHESIZE(string, logistics, Logistics);
	// 单据附件
	MYSQL_SYNTHESIZE(string, file, File);
	// 备注信息
	MYSQL_SYNTHESIZE(string, data, Data);
	// 扩展信息
	MYSQL_SYNTHESIZE(string, more, More);
	// 审核状态
	MYSQL_SYNTHESIZE(int, examine, Examine);
	// 费用状态
	MYSQL_SYNTHESIZE(int, cse, Cse);
	// 核对状态
	MYSQL_SYNTHESIZE(int, check, Check);
	// 制单人
	MYSQL_SYNTHESIZE(string, user, User);
public:
	EntryDO() : BaseDO("entry")
	{
		MYSQL_ADD_FIELD_PK("id", "s", id);
		MYSQL_ADD_FIELD("supplier", "s", supplier);
		MYSQL_ADD_FIELD("frame", "s", frame);
		MYSQL_ADD_FIELD("time", "s", time);
		MYSQL_ADD_FIELD("number", "s", number);
		MYSQL_ADD_FIELD("type", "i", type);
		MYSQL_ADD_FIELD("total", "d", total);
		MYSQL_ADD_FIELD("cost", "d", cost);
		MYSQL_ADD_FIELD("people", "s", people);
		MYSQL_ADD_FIELD("logistics", "s", logistics);
		MYSQL_ADD_FIELD("file", "s", file);
		MYSQL_ADD_FIELD("data", "s", data);
		MYSQL_ADD_FIELD("more", "s", more);
		MYSQL_ADD_FIELD("examine", "i", examine);
		MYSQL_ADD_FIELD("cse", "i", cse);
		MYSQL_ADD_FIELD("check", "i", check);
		MYSQL_ADD_FIELD("user", "s", user);
	}
};

// 为EntryDO对象指针设定一个别名，使用
typedef std::shared_ptr<EntryDO> PtrEntryDO;
#endif // !_ENTRY_DO_