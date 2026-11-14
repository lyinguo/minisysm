#pragma once
#ifndef _DICT_TYPE_DO_
#define _DICT_TYPE_DO_
#include "../DoInclude.h"

/**
 * 字典类型数据对象
 */
class DictTypeDO : public BaseDO
{
	// 唯一标识
	MYSQL_SYNTHESIZE(string, id, Id);
	// 字典类型名称
	MYSQL_SYNTHESIZE(string, name, Name);
	// 字典类型编码
	MYSQL_SYNTHESIZE(string, code, Code);
	// 备注
	MYSQL_SYNTHESIZE(string, remark, Remark);
public:
	DictTypeDO() : BaseDO("dict_type")
	{
		MYSQL_ADD_FIELD_PK("id", "s", id);
		MYSQL_ADD_FIELD("name", "s", name);
		MYSQL_ADD_FIELD("code", "s", code);
		MYSQL_ADD_FIELD("remark", "s", remark);
	}
};

// 为DictTypeDO对象指针设定一个别名，使用
typedef std::shared_ptr<DictTypeDO> PtrDictTypeDO;
#endif // !_DICT_TYPE_DO_