#pragma once

#include "../../GlobalInclude.h"
#include"domain/query/PageQuery.h"
#include OATPP_CODEGEN_BEGIN(DTO)
class Cus_State_OneDTO :public oatpp::DTO			//隐藏明细DTO
{
	DTO_INIT(Cus_State_OneDTO, DTO);

	//单据类型  
	API_DTO_FIELD_DEFAULT(String, mold, ZH_WORDS_GETTER("Cus_State_OneDTO.mold"));
	//所属组织  
	API_DTO_FIELD_DEFAULT(String, frame, ZH_WORDS_GETTER("Cus_State_OneDTO.frame"));
	//单据时间 
	API_DTO_FIELD_DEFAULT(String, time, ZH_WORDS_GETTER("Cus_State_OneDTO.time"));
	//单据编号  
	API_DTO_FIELD_DEFAULT(String, number, ZH_WORDS_GETTER("Cus_State_OneDTO.number"));
	//优惠金额
	API_DTO_FIELD_DEFAULT(Float64, cost, ZH_WORDS_GETTER("Cus_State_OneDTO.cost"));
	//应收金额
	API_DTO_FIELD_DEFAULT(Float64, actual, ZH_WORDS_GETTER("Cus_State_OneDTO.actual"));
	//实收金额
	API_DTO_FIELD_DEFAULT(Float64, money, ZH_WORDS_GETTER("Cus_State_OneDTO.money"));
	//备注  data
	API_DTO_FIELD_DEFAULT(String, data, ZH_WORDS_GETTER("Cus_State_OneDTO.data"));
};

class Cus_State_OnepageDTO :public PageDTO<Cus_State_OneDTO::Wrapper>
{
	DTO_INIT(Cus_State_OnepageDTO, PageDTO<Cus_State_OneDTO::Wrapper>);
};

class Cus_State_AllDTO :public Cus_State_OneDTO			//明确明细DTO
{
	DTO_INIT(Cus_State_AllDTO, Cus_State_OneDTO);
	//名称
	API_DTO_FIELD_DEFAULT(String, goods, ZH_WORDS_GETTER("Cus_State_AllDTO.goods"));
	//属性
	API_DTO_FIELD_DEFAULT(String, attr, ZH_WORDS_GETTER("Cus_State_AllDTO.attr"));
	//单位
	API_DTO_FIELD_DEFAULT(String, unit, ZH_WORDS_GETTER("Cus_State_AllDTO.unit"));
	//数量
	API_DTO_FIELD_DEFAULT(Int32, nums, ZH_WORDS_GETTER("Cus_State_AllDTO.nums"));
	//折扣额
	API_DTO_FIELD_DEFAULT(Float64, dsc, ZH_WORDS_GETTER("Cus_State_AllDTO.dsc"));
	//金额
	API_DTO_FIELD_DEFAULT(Float64, total, ZH_WORDS_GETTER("Cus_State_AllDTO.total"));
	//税额
	API_DTO_FIELD_DEFAULT(Float64, tat, ZH_WORDS_GETTER("Cus_State_AllDTO.tat"));
	//价税合计
	API_DTO_FIELD_DEFAULT(Float64, tpt, ZH_WORDS_GETTER("Cus_State_AllDTO.tpt"));
};

class Cus_State_AllpageDTO :public PageDTO<Cus_State_AllDTO::Wrapper>
{
	DTO_INIT(Cus_State_AllpageDTO, PageDTO<Cus_State_AllDTO::Wrapper>);
};
#include OATPP_CODEGEN_END(DTO)
