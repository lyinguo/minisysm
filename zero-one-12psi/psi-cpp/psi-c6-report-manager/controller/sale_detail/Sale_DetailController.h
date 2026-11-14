#pragma once


#include"domain/vo/BaseJsonVO.h"
#include"domain/query/PageQuery.h"
#include"../../Macros.h"
#include"ServerInfo.h"
#include"ApiHelper.h"
#include"../../domain/vo/sale_detail/Sale_DetailVO.h"
#include"../../domain/query/sale_detail/Sale_DetailQuery.h"
#include"../../domain/dto/sale_detail/Sale_DetailDTO.h"

#include OATPP_CODEGEN_BEGIN(ApiController)



class Sale_DetailController :public oatpp::web::server::api::ApiController
{
	//定义控制访问入口
	API_ACCESS_DECLARE(Sale_DetailController);
public:			//定义接口

	// 3.1 定义查询接口描述
	ENDPOINT_INFO(querySample) {
		// 定义接口标题
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("Sale_Detail.get.summary"));
		// 定义默认授权参数（可选定义，如果定义了，下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
		API_DEF_ADD_AUTH();
		// 定义响应参数格式
		API_DEF_ADD_RSP_JSON_WRAPPER(Sale_DetailpageJsonVO);
		// 定义标签
		API_DEF_ADD_TAG(ZH_WORDS_GETTER("Sale_DetailController.tags"));
		// 定义分页查询参数描述
		API_DEF_ADD_PAGE_PARAMS();
		// 定义其他查询参数描述

		//客户名称
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("Sale_Detail.field.name"), "li ming", false);
		//商品名称
		API_DEF_ADD_QUERY_PARAMS(String, "object", ZH_WORDS_GETTER("Sale_Detail.field.object"), "object", false);
		//单据编号
		API_DEF_ADD_QUERY_PARAMS(String, "number", ZH_WORDS_GETTER("Sale_Detail.field.Number"), "Number", false);
		//仓库
		API_DEF_ADD_QUERY_PARAMS(String, "warehouse", ZH_WORDS_GETTER("Sale_Detail.field.warehouse"), "c6", false);
		//起始时间
		API_DEF_ADD_QUERY_PARAMS(String, "starttime", ZH_WORDS_GETTER("Sale_Detail.field.starttime"), "starttime", false);
		//结束时间
		API_DEF_ADD_QUERY_PARAMS(String, "endtime", ZH_WORDS_GETTER("Sale_Detail.field.endtime"), "endtime", false);
		//单据类型
		API_DEF_ADD_QUERY_PARAMS(String, "type", ZH_WORDS_GETTER("Sale_Detail.field.type"), "type", false);
		//备注信息
		API_DEF_ADD_QUERY_PARAMS(String, "data", ZH_WORDS_GETTER("Sale_Detail.field.data"), "data", false);
	}
	// 3.2 定义查询接口处理
	ENDPOINT(API_M_GET, "/saleDetail", querySample, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		// 解析查询参数为Query领域模型
		API_HANDLER_QUERY_PARAM(sa_DeQuery, Sale_DetailQuery, queryParams);
		// 呼叫执行函数响应结果
		API_HANDLER_RESP_VO(execQuerySale_Detail(sa_DeQuery));
	}

	// 3.1 定义导出接口描述
	API_DEF_ENDPOINT_INFO_QUERY_AUTH(ZH_WORDS_GETTER("Sale_Detail.export.summary"), exportSample, Sale_DetailQuery, Void, ZH_WORDS_GETTER("Sale_DetailController.tags"));
	// 3.2 定义导出接口处理
	API_HANDLER_ENDPOINT_OPTION_AUTH(API_M_GET, "/saleDetail/export", exportSample, QUERIES(QueryParams, queryParams),
		API_HANDLER_QUERY_PARAM(saDetailQuery, Sale_DetailQuery, queryParams); return execExportSa_Detail(saDetailQuery););


private:		//定义接口执行函数
	Sale_DetailpageJsonVO::Wrapper execQuerySale_Detail(const Sale_DetailQuery::Wrapper& query);
	std::shared_ptr<OutgoingResponse> execExportSa_Detail(const Sale_DetailQuery::Wrapper& query);
};

#include OATPP_CODEGEN_END(ApiController)