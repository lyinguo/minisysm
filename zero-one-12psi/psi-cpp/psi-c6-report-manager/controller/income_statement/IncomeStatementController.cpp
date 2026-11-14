#include "stdafx.h"
#include "service/income_statement/IncomeStatementService.h"
#include "../ApiDeclarativeServicesHelper.h"
#include "ExcelComponent.h"
#include "SimpleDateTimeFormat.h"
//FastDFS
#include "ServerInfo.h"
#include "NacosClient.h"
#include "FastDfsClient.h"
#include "IncomeStatementController.h"

//查询接口
IncomeStatementPageVO::Wrapper IncomeStatementController::execQuerySDR(const IncomeStatementQuery::Wrapper& query)
{
	auto jvo = IncomeStatementPageVO::createShared();

	//非空校验
	if (query->end_date || query->start_date)
	{
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}

	IncomeStatementService service;

	auto result = service.listAll(query);

	jvo->success(result);

	return jvo;
}
//导出接口
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> IncomeStatementController::execQuerySDRX(const IncomeStatementQuery::Wrapper& query)
{
	//定义一个Service
	IncomeStatementService service;

	//查询数据
	auto result = service.listAll(query);

	//将数据写入excel中
	auto buff = ExcelComponent().writeVectorToBuff(
		"income_statement",
		[result](ExcelComponent* ex)
		{
			ex->addHeader({
				ZH_WORDS_GETTER("income_statement.field.serial_number"),
				ZH_WORDS_GETTER("income_statement.field.item"),
				ZH_WORDS_GETTER("income_statement.field.amount")
				});

			//写入数据
			int row = 2;
			int col = 1;
			for (auto item : *(result->rows.get()))
			{
				col = 1;
				ex->setCellValue(row, col++, item->serial_number);
				ex->setCellValue(row, col++, item->item);
				ex->setCellValue(row, col++, std::to_string(item->amount));
				ex->setRowProperties(row++);
			}// ex->setCellValue(row, col++, std::to_string(item->price));
		});
	//组装下发数据
	const char* charData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(charData, buff.size());

	//测试将报表上传到fastdfs
	ZO_CREATE_DFS_CLIENT_URL(dfs, urlPrefix);
	string filepath = dfs.uploadFile(charData, buff.size(), "xlsx");
	string downloadUrl = urlPrefix + filepath;
	OATPP_LOGD("Multipart", "download url='%s'", downloadUrl.c_str());

	//创建响应头
	auto response = createResponse(Status::CODE_200, fstring);
	std::string filename = "rp-sales_income_statement-" + SimpleDateTimeFormat::format() + ".xlsx";
	/*std::string filename = "E://MyTest.xlsx";*/
	response->putHeader("Content-Disposition", "attachment; filename=" + filename);
	response->putHeader(Header::CONTENT_TYPE, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
	return response;
}