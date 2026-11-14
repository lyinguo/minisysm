#pragma once
#ifndef _MYSAMPLE_H_
#define _MYSAMPLE_H_


#include"ApiHelper.h"
#include"domain/vo/BaseJsonVO.h"
#include"domain/query/PageQuery.h"
#include"../../Macros.h"
#include"ServerInfo.h"
#include"../../domain/vo/customer_statement/Cus_StateVO.h"
#include"../../domain/query/customer_statement/Cus_StateQuery.h"
#include"../../domain/dto/customer_statement/Cus_StateDTO.h"

#include OATPP_CODEGEN_BEGIN(ApiController)

#define API_TAG ZH_WORDS_GETTER("Cus_StateController.tags.t1")
#define API_TAG2 ZH_WORDS_GETTER("Cus_StateController.tags.t1")
class Cus_StateController :public oatpp::web::server::api::ApiController
{
	//定义控制访问入口
	API_ACCESS_DECLARE(Cus_StateController);
public:			//定义接口
	//定义客户查询接口描述
	ENDPOINT_INFO(querySample) {
		// 定义接口标题
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("Cus_State.get.summary"));
		// 定义默认授权参数（可选定义，如果定义了，下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
		API_DEF_ADD_AUTH();
		// 定义响应参数格式
		API_DEF_ADD_RSP_JSON_WRAPPER(Cus_State_AllpageJsonVO);
		// 定义标签
		API_DEF_ADD_TAG(ZH_WORDS_GETTER("Cus_StateController.tags.t1"));
		// 定义分页查询参数描述
		API_DEF_ADD_PAGE_PARAMS();
		// 定义其他查询参数描述
		API_DEF_ADD_QUERY_PARAMS(String, "starttime", ZH_WORDS_GETTER("Cus_State.field.starttime"), "2024-10-10", false);
		API_DEF_ADD_QUERY_PARAMS(String, "endtime", ZH_WORDS_GETTER("Cus_State.field.endtime"), "2025-10-10", false);
		API_DEF_ADD_QUERY_PARAMS(Boolean, "is_detail", ZH_WORDS_GETTER("Cus_State.field.is_detail"), "false", true);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("Cus_State.field.name"), ZH_WORDS_GETTER("Cus_State.field.sample"), true);
	}
	//定义客户查询接口处理
	ENDPOINT(API_M_GET, "/customerState", querySample, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		// 解析查询参数为Query领域模型
		API_HANDLER_QUERY_PARAM(Cus_AllQuery, Cus_StateQuery, queryParams);
		// 呼叫执行函数响应结果
		if(Cus_AllQuery->is_detail) API_HANDLER_RESP_VO(Cus_StateexecQueryAll(Cus_AllQuery));
		else API_HANDLER_RESP_VO(Cus_StateexecQueryOne(Cus_AllQuery));
	}


	// 3.1 定义导出接口描述
	ENDPOINT_INFO(exportSample) {
		API_DEF_ADD_AUTH();
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("Cus_State.export.summary"));
		API_DEF_ADD_TAG(API_TAG2);
		API_DEF_ADD_RSP_JSON(Void);
		API_DEF_QUERY_PARAM_BUILD(Cus_StateQuery);
		// 定义其他查询参数描述
		API_DEF_ADD_QUERY_PARAMS(String, "starttime", ZH_WORDS_GETTER("Cus_State.field.starttime"), "2024-10-10", false);
		API_DEF_ADD_QUERY_PARAMS(String, "endtime", ZH_WORDS_GETTER("Cus_State.field.endtime"), "2025-10-10", false);
		API_DEF_ADD_QUERY_PARAMS(Boolean, "is_detail", ZH_WORDS_GETTER("Cus_State.field.is_detail"), "false", true);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("Cus_State.field.name"), ZH_WORDS_GETTER("Cus_State.field.sample"), true);
	}

	//API_DEF_ENDPOINT_INFO_QUERY_AUTH(ZH_WORDS_GETTER("Cus_State.export.summary"), exportSample, Cus_StateQuery, Void,API_TAG2);

	// 3.2 定义导出接口处理
	ENDPOINT(API_M_GET, "/customerState/export", exportSample, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(Cus_AllQuery, Cus_StateQuery, queryParams);
		return execExportAllCus(Cus_AllQuery);
	}

	//API_HANDLER_ENDPOINT_OPTION_AUTH(API_M_GET, "/customerState/export", exportSample, QUERIES(QueryParams, queryParams),
	//	API_HANDLER_QUERY_PARAM(Cus_AllQuery, Cus_StateQuery, queryParams); return execExportAllCus(Cus_AllQuery););


private:		//定义接口执行函数
	Cus_State_AllpageJsonVO::Wrapper Cus_StateexecQueryAll(const Cus_StateQuery::Wrapper& query);
	Cus_State_OnepageJsonVO::Wrapper Cus_StateexecQueryOne(const Cus_StateQuery::Wrapper& query);
	std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> execExportAllCus(const Cus_StateQuery::Wrapper& query);
};

#include OATPP_CODEGEN_END(ApiController)
#endif 