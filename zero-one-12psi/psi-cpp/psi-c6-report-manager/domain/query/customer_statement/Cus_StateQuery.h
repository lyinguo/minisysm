#ifndef _CUS_STATEQUERY_H_
#define _CUS_STATEQUERY_H_

#include"../../GlobalInclude.h"
#include"domain/query/PageQuery.h"
#include OATPP_CODEGEN_BEGIN(DTO)
class Cus_StateQuery :public PageQuery
{
	
	DTO_INIT(Cus_StateQuery, PageQuery);

	//客户名称
	API_DTO_FIELD_DEFAULT(String, name, ZH_WORDS_GETTER("Cus_StateQuery.name"));

	//是否明细
	API_DTO_FIELD_DEFAULT(Boolean, is_detail, ZH_WORDS_GETTER("Cus_StateQuery.is_detail"));

	//起始时间
	API_DTO_FIELD_DEFAULT(String,starttime, ZH_WORDS_GETTER("Cus_StateQuery.starttime"));

	//结束时间
	API_DTO_FIELD_DEFAULT(String,endtime, ZH_WORDS_GETTER("Cus_StateQuery.endtime"));
};
#include OATPP_CODEGEN_END(DTO)
#endif