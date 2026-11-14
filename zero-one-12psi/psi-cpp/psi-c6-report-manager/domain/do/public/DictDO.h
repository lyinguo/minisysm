#pragma once
#ifndef _DICT_DO_
#define _DICT_DO_
#include "../DoInclude.h"

/**
 * 字典数据对象
 */
class DictDO : public BaseDO
{
	// 唯一标识
	MYSQL_SYNTHESIZE(string, id, Id);
	// 所属字典类型
	MYSQL_SYNTHESIZE(string, tid, Tid);
	// 字典名称
	MYSQL_SYNTHESIZE(string, name, Name);
	// 字典值
	MYSQL_SYNTHESIZE(string, value, Value);
	// 备注
	MYSQL_SYNTHESIZE(string, remark, Remark);
public:
	DictDO() : BaseDO("dict")
	{
		MYSQL_ADD_FIELD_PK("id", "s", id);
		MYSQL_ADD_FIELD("tid", "s", tid);
		MYSQL_ADD_FIELD("name", "s", name);
		MYSQL_ADD_FIELD("value", "s", value);
		MYSQL_ADD_FIELD("remark", "s", remark);
	}
};

// 为DictDO对象指针设定一个别名，使用
typedef std::shared_ptr<DictDO> PtrDictDO;
#endif // !_DICT_DO_