#pragma once


#include"../../GlobalInclude.h"
#include"domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)
class Sale_DetailQuery :public PageQuery
{
	DTO_INIT(Sale_DetailQuery, PageQuery);
	
	//客户名称
	DTO_FIELD(String, name);
	DTO_FIELD_INFO(name)
	{
		info->description = ZH_WORDS_GETTER("Sale_Detail_Query.name");
	}
	//商品名称
	DTO_FIELD(String, object);
	DTO_FIELD_INFO(object) {
		info->description = ZH_WORDS_GETTER("Sale_Detail_Query.object");
	}
	//单据编号
	DTO_FIELD(String,number);
	DTO_FIELD_INFO(number)
	{
		info->description = ZH_WORDS_GETTER("Sale_Detail_Query.number");
	}
	//仓库
	DTO_FIELD(String, warehouse);
	DTO_FIELD_INFO(warehouse)
	{
		info->description = ZH_WORDS_GETTER("Sale_Detail_Query.warehouse");
	}
	//起始时间
	DTO_FIELD(String, starttime);
	DTO_FIELD_INFO(starttime)
	{
		info->description = ZH_WORDS_GETTER("Sale_Detail_Query.starttime");
	}
	//结束时间
	DTO_FIELD(String, endtime);
	DTO_FIELD_INFO(endtime)
	{
		info->description = ZH_WORDS_GETTER("Sale_Detail_Query.endtime");
	}
	//单据类型
	DTO_FIELD(String, type);
	DTO_FIELD_INFO(type)
	{
		info->description = ZH_WORDS_GETTER("Sale_Detail_Query.type");
	}
	//备注信息
	DTO_FIELD(String, data);
	DTO_FIELD_INFO(data)
	{
		info->description = ZH_WORDS_GETTER("Sale_Detail_Query.data");
	}
};

#include OATPP_CODEGEN_END(DTO)