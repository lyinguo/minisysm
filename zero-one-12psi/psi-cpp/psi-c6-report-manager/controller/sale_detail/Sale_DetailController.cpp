
#include "stdafx.h"
#include "Sale_DetailController.h"
#include "../../service/sale_detail/Sale_DetailService.h"
#include "../ApiDeclarativeServicesHelper.h"
#include "ExcelComponent.h"
#include "SimpleDateTimeFormat.h"
#include "Macros.h"
#include "NacosClient.h"
#include "gtest/gtest.h"
#include "FastDfsClient.h"


Sale_DetailpageJsonVO::Wrapper Sale_DetailController::execQuerySale_Detail(const Sale_DetailQuery::Wrapper& query)
{

	//校验数据
	//sale_detail无必要传递参数

	//定义一个Service
	Sale_DetailService service;

	//查询数据
	auto result = service.listAll(query);

	//响应结果
	auto jvo = Sale_DetailpageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}


std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> Sale_DetailController::execExportSa_Detail(const Sale_DetailQuery::Wrapper& query)
{
	// 定义一个Service
	Sale_DetailService service;
	// 查询数据
	auto result = service.listAll(query);
	// 将数据写入到Excel中
	auto buff = ExcelComponent().writeVectorToBuff("sale_detail",
		[result](ExcelComponent* ex) {
			// 写入表头
			ex->addHeader({
				ZH_WORDS_GETTER("Sale_DetailDTO.mold") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.frame") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.customer") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.time") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.number") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.goods") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.attr") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.warehouse") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.price") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.unit") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.nums") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.dsc") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.total") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.tat") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.tpt") ,
				ZH_WORDS_GETTER("Sale_DetailDTO.data") 
				});
			// 写入数据
			int row = 2;
			int col = 1;
			for (auto item : *(result->rows.get())) {
				col = 1;
				ex->setCellValue(row, col++, item->mold);
				ex->setCellValue(row, col++, item->frame);
				ex->setCellValue(row, col++, item->customer);
				ex->setCellValue(row, col, item->time);
				ex->setCellValue(row, col, item->number);
				ex->setCellValue(row, col, item->goods);
				ex->setCellValue(row, col, item->attr);
				ex->setCellValue(row, col, item->warehouse);
				ex->setCellValue(row, col, std::to_string(item->price));
				ex->setCellValue(row, col, item->unit);
				ex->setCellValue(row, col, std::to_string(item->nums));
				ex->setCellValue(row, col, std::to_string(item->dsc));
				ex->setCellValue(row, col, std::to_string(item->total));
				ex->setCellValue(row, col, std::to_string(item->tat));
				ex->setCellValue(row, col, std::to_string(item->tpt));
				ex->setCellValue(row, col, item->data);
				ex->setRowProperties(row++);
			}
		});

	// 组装下发数据
	const char* charData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(charData, buff.size());

	// 测试将报表上传到fastdfs
	ZO_CREATE_DFS_CLIENT_URL(dfs, urlPrefix);
	string filepath = dfs.uploadFile(charData, buff.size(), "xlsx");

	// 打印文件上传成功后的下载地址
	string downloadUrl = urlPrefix + filepath;
	OATPP_LOGD("Multipart", "download url='%s'", downloadUrl.c_str());

	// 创建响应头
	auto response = createResponse(Status::CODE_200, fstring);
	// 设置响应头信息
	std::string filename = "rp-sample-" + SimpleDateTimeFormat::format() + ".xlsx";
	response->putHeader("Content-Disposition", "attachment; filename=" + filename);
	response->putHeader(Header::CONTENT_TYPE, " application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

	// 影响成功结果
	return response;
}
