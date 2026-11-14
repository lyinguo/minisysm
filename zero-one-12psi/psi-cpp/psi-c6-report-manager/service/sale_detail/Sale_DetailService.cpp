
#include "stdafx.h"
#include "Sale_DetailService.h"
#include "../../dao/sale_detail/Sale_DetailDAO.h"
#include "id/UuidFacade.h"
Sale_DetailPageDTO::Wrapper Sale_DetailService::listAll(const Sale_DetailQuery::Wrapper& query)
{
	//构建返回对象
	auto pages = Sale_DetailPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	//查询数据总条数
	Sale_DetailDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;

	// 分页查询数据
	pages->total = count;
	pages->calcPages();
	list<Sale_DetailViewDO> result = dao.selectWithPage(query);
	// 将DO转换成DTO
	for (Sale_DetailViewDO& sub : result)
	{
		auto dto = Sale_DetailDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, mold, mold_method, frame, frame_method, customer, customer_method, time, time_method);
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, number, number_method, goods, goods_method, attr, attr_method, warehouse, warehouse_method);
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, price, price_method, unit, unit_method, nums, nums_method, dsc, dsc_method, total, total_method);
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, tat, tat_method, tpt, tpt_method, data, data_method);
		pages->addData(dto);
	}
	return pages;
}
