#include "stdafx.h"
#include "ApiHelper.h"
#include "ExcelComponent.h"
#include "SalesRankingReport.h"
#include "../../service/sales_ranking_report/SalesRankingReportService.h"

SalesRankingReportJsonVO::Wrapper SalesRankingReport::execSalesRankingTableQuery(const SalesRankingTableQuery::Wrapper& query) {
	auto jvo = SalesRankingReportJsonVO::createShared();
	if (!query->pageIndex || !query->pageSize) {
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}
	SalesRankingReportService service;
	auto dto = service.listAll(query);
	jvo->success(dto);
	return jvo;
}

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> SalesRankingReport::execExportSalesRankingTableQuery(const SalesRankingTableQuery::Wrapper& query) {
	SalesRankingReportService service;
	auto result = service.listAll(query);
	auto buff = ExcelComponent().writeVectorToBuff("sales_ranking_report",
		[result](ExcelComponent* ex) {
			//添加表头
			ex->addHeader({
				ZH_WORDS_GETTER("sales_ranking_report.field.name"),
				ZH_WORDS_GETTER("sales_ranking_report.field.number"),
				ZH_WORDS_GETTER("sales_ranking_report.field.spec"),
				ZH_WORDS_GETTER("sales_ranking_report.field.attr"),
				ZH_WORDS_GETTER("sales_ranking_report.field.unit"),
				ZH_WORDS_GETTER("sales_ranking_report.field.nums"),
				ZH_WORDS_GETTER("sales_ranking_report.field.dsc"),
				ZH_WORDS_GETTER("sales_ranking_report.field.tat"),
				ZH_WORDS_GETTER("sales_ranking_report.field.tpt"),
				ZH_WORDS_GETTER("sales_ranking_report.field.bct"),
				ZH_WORDS_GETTER("sales_ranking_report.field.uct"),
				ZH_WORDS_GETTER("sales_ranking_report.field.gpt"),
				ZH_WORDS_GETTER("sales_ranking_report.field.gpr")
				});
			int row = 2;
			int col = 1;
			//填充表数据
			for (auto item : *(result->rows.get())) {
				col = 1;
				ex->setCellValue(row, col++, item->name);
				ex->setCellValue(row, col++, item->number);
				ex->setCellValue(row, col++, item->spec);
				ex->setCellValue(row, col++, item->attr);
				ex->setCellValue(row, col++, item->unit);
				ex->setCellValue(row, col++, std::to_string(item->nums));
				ex->setCellValue(row, col++, std::to_string(item->dsc));
				ex->setCellValue(row, col++, std::to_string(item->tat));
				ex->setCellValue(row, col++, std::to_string(item->tpt));
				ex->setCellValue(row, col++, std::to_string(item->bct));
				ex->setCellValue(row, col++, std::to_string(item->uct));
				ex->setCellValue(row, col++, std::to_string(item->gpt));
				ex->setCellValue(row, col++, item->gpr);

				ex->setRowProperties(row++);
			}
		}
	);
	const char* charData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(charData, buff.size());

	//构建相应头
	auto response = createResponse(Status::CODE_200, fstring);

	// 设置响应头信息
	std::string filename = "sales_ranking_report.xlsx";
	response->putHeader("Content-Disposition", "attachment; filename=" + filename);
	response->putHeader(Header::CONTENT_TYPE, " application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

	return response;
}
