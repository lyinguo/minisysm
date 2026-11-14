
#include "stdafx.h"
#include "Cus_StateController.h"
#include "../../service/customer_statement/Cus_StateService.h"
#include "../ApiDeclarativeServicesHelper.h"
#include "ExcelComponent.h"
#include "SimpleDateTimeFormat.h"
#include "Macros.h"
#include "NacosClient.h"
#include "gtest/gtest.h"
#include "FastDfsClient.h"


Cus_State_AllpageJsonVO::Wrapper Cus_StateController::Cus_StateexecQueryAll(const Cus_StateQuery::Wrapper& query)
{
    //定义一个Service
    Cus_StateService service;
	
    //查询数据
    auto result = service.listAll(query);
	
    //响应结果
    auto ans = Cus_State_AllpageJsonVO::createShared();
    ans->success(result);
    return ans;
}

 std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> Cus_StateController::execExportAllCus(const Cus_StateQuery::Wrapper& query)
 {
	 if (query->is_detail)
	 {
		 // 定义一个Service
		 Cus_StateService service;
		 // 查询数据
		 auto result = service.listAll(query);
		 // 将数据写入到Excel中
		 auto buff = ExcelComponent().writeVectorToBuff("customer_statement",
			 [result](ExcelComponent* ex) {
				 // 写入表头
				 ex->addHeader({
					 ZH_WORDS_GETTER("Cus_StateController.mold") ,
					 ZH_WORDS_GETTER("Cus_StateController.frame") ,
					 ZH_WORDS_GETTER("Cus_StateController.time") ,
					 ZH_WORDS_GETTER("Cus_StateController.number") ,
					 ZH_WORDS_GETTER("Cus_StateController.cost") ,
					 ZH_WORDS_GETTER("Cus_StateController.actual") ,
					 ZH_WORDS_GETTER("Cus_StateController.money") ,
					 ZH_WORDS_GETTER("Cus_StateController.data") ,
					 ZH_WORDS_GETTER("Cus_StateController.goods") ,
					 ZH_WORDS_GETTER("Cus_StateController.attr") ,
					 ZH_WORDS_GETTER("Cus_StateController.unit") ,
					 ZH_WORDS_GETTER("Cus_StateController.nums") ,
					 ZH_WORDS_GETTER("Cus_StateController.dsc") ,
					 ZH_WORDS_GETTER("Cus_StateController.total") ,
					 ZH_WORDS_GETTER("Cus_StateController.tat") ,
					 ZH_WORDS_GETTER("Cus_StateController.tpt")
					 });
				 // 写入数据
				 int row = 2;
				 int col = 1;
				 for (auto item : *(result->rows.get())) {
					 col = 1;
					 ex->setCellValue(row, col++, item->mold);
					 ex->setCellValue(row, col++, item->frame);
					 ex->setCellValue(row, col++, item->time);
					 ex->setCellValue(row, col, item->number);
					 ex->setCellValue(row, col, std::to_string(item->cost));
					 ex->setCellValue(row, col, std::to_string(item->actual));
					 ex->setCellValue(row, col, std::to_string(item->money));
					 ex->setCellValue(row, col, item->data);
					 ex->setCellValue(row, col, item->goods);
					 ex->setCellValue(row, col, item->attr);
					 ex->setCellValue(row, col, item->unit);
					 ex->setCellValue(row, col, std::to_string(item->nums));
					 ex->setCellValue(row, col, std::to_string(item->dsc));
					 ex->setCellValue(row, col, std::to_string(item->total));
					 ex->setCellValue(row, col, std::to_string(item->tat));
					 ex->setCellValue(row, col, std::to_string(item->tpt));
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
	 else
	 {
		 // 定义一个Service
		 Cus_StateService service;
		 // 查询数据
		 auto result = service.listOne(query);
		 // 将数据写入到Excel中
		 auto buff = ExcelComponent().writeVectorToBuff("customer_statement",
			 [result](ExcelComponent* ex) {
				 // 写入表头
				 ex->addHeader({
					 ZH_WORDS_GETTER("Cus_StateController.mold") ,
					 ZH_WORDS_GETTER("Cus_StateController.frame") ,
					 ZH_WORDS_GETTER("Cus_StateController.time") ,
					 ZH_WORDS_GETTER("Cus_StateController.number") ,
					 ZH_WORDS_GETTER("Cus_StateController.cost") ,
					 ZH_WORDS_GETTER("Cus_StateController.actual") ,
					 ZH_WORDS_GETTER("Cus_StateController.money") ,
					 ZH_WORDS_GETTER("Cus_StateController.data") ,
					 });
				 // 写入数据
				 int row = 2;
				 int col = 1;
				 for (auto item : *(result->rows.get())) {
					 col = 1;
					 ex->setCellValue(row, col++, item->mold);
					 ex->setCellValue(row, col++, item->frame);
					 ex->setCellValue(row, col++, item->time);
					 ex->setCellValue(row, col, item->number);
					 ex->setCellValue(row, col, std::to_string(item->cost));
					 ex->setCellValue(row, col, std::to_string(item->actual));
					 ex->setCellValue(row, col, std::to_string(item->money));
					 ex->setCellValue(row, col, item->data);
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
 }


 Cus_State_OnepageJsonVO::Wrapper Cus_StateController::Cus_StateexecQueryOne(const Cus_StateQuery::Wrapper& query)
 {
     //定义一个Service
     Cus_StateService service;
	 
     //查询数据
     auto result = service.listOne(query);
	 
     //响应结果
     auto ans = Cus_State_OnepageJsonVO::createShared();
     ans->success(result);
     return ans;
 }
