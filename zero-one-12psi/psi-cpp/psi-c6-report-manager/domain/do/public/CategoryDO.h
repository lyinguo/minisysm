#pragma once 
#include"../DoInclude.h"
class CategoryDO :BaseDO
{
	//唯一标识
	MYSQL_SYNTHESIZE(string, id, Id);
	//所属类别
	MYSQL_SYNTHESIZE(string, pid, Pid);
	//类别名称
	MYSQL_SYNTHESIZE(string, name, Name);
	//类别排序
	MYSQL_SYNTHESIZE(int, sort, Sort);
	//备注信息
	MYSQL_SYNTHESIZE(string, data, Data);
public:
	CategoryDO() :BaseDO("category")
	{
		MYSQL_ADD_FIELD_PK("id","s", Id);
		MYSQL_ADD_FIELD("pid", "s", Pid);
		MYSQL_ADD_FIELD("name", "s", Name);
		MYSQL_ADD_FIELD("sort", "i", Sort);
		MYSQL_ADD_FIELD("data", "s", Data);
	}
};

typedef std::shared_ptr<CategoryDO> PtrCategoryDO;