#pragma once

#include"../../GlobalInclude.h"
#include OATPP_CODEGEN_BEGIN(DTO)
class Sale_DetailDTO :public oatpp::DTO
{
	DTO_INIT(Sale_DetailDTO, DTO);

	//单据类型
	API_DTO_FIELD_DEFAULT(String, mold, ZH_WORDS_GETTER("Sale_DetailDTO.mold"));
	//所属组织
	API_DTO_FIELD_DEFAULT(String, frame, ZH_WORDS_GETTER("Sale_DetailDTO.frame"));
	//客户
	API_DTO_FIELD_DEFAULT(String, customer, ZH_WORDS_GETTER("Sale_DetailDTO.customer"));
	//单据时间
	API_DTO_FIELD_DEFAULT(String, time, ZH_WORDS_GETTER("Sale_DetailDTO.time"));
	//单据编号
	API_DTO_FIELD_DEFAULT(String, number, ZH_WORDS_GETTER("Sale_DetailDTO.number"));
	//商品名称
	API_DTO_FIELD_DEFAULT(String, goods, ZH_WORDS_GETTER("Sale_DetailDTO.goods"));
	//辅助类型
	API_DTO_FIELD_DEFAULT(String, attr, ZH_WORDS_GETTER("Sale_DetailDTO.attr"));
	//仓库
	API_DTO_FIELD_DEFAULT(String, warehouse, ZH_WORDS_GETTER("Sale_DetailDTO.warehouse"));
	//单价
	API_DTO_FIELD_DEFAULT(Float32, price, ZH_WORDS_GETTER("Sale_DetailDTO.price"));
	//单位
	API_DTO_FIELD_DEFAULT(String, unit, ZH_WORDS_GETTER("Sale_DetailDTO.unit"));
	//数量
	API_DTO_FIELD_DEFAULT(Int32, nums, ZH_WORDS_GETTER("Sale_DetailDTO.nums"));
	//折扣额
	API_DTO_FIELD_DEFAULT(Float32, dsc, ZH_WORDS_GETTER("Sale_DetailDTO.dsc"));
	//金额
	API_DTO_FIELD_DEFAULT(Float32, total, ZH_WORDS_GETTER("Sale_DetailDTO.total"));
	//税额
	API_DTO_FIELD_DEFAULT(Float32, tat, ZH_WORDS_GETTER("Sale_DetailDTO.tat"));
	//价税合计
	API_DTO_FIELD_DEFAULT(Float32, tpt, ZH_WORDS_GETTER("Sale_DetailDTO.tpt"));
	//备注
	API_DTO_FIELD_DEFAULT(String, data, ZH_WORDS_GETTER("Sale_DetailDTO.data"));
};

class Sale_DetailPageDTO :public PageDTO<Sale_DetailDTO::Wrapper>
{
	DTO_INIT(Sale_DetailPageDTO, PageDTO<Sale_DetailDTO::Wrapper>);
};
#include OATPP_CODEGEN_END(DTO)