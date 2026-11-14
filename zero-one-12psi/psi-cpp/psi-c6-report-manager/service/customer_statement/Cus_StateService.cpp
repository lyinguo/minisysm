#include "stdafx.h"
#include "Cus_StateService.h"
#include "../../dao/customer_statement/Cus_StateDAO.h"
#include "id/UuidFacade.h"

Cus_State_OnepageDTO::Wrapper Cus_StateService::listOne(const Cus_StateQuery::Wrapper& query)
{
	//构建返回对象
	auto pages = Cus_State_OnepageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	//查询数据总条数
	Cus_StateDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;

	// 分页查询数据
	pages->total = count;
	pages->calcPages();
	list<Cus_StateOneViewDO> result = dao.selectOneWithPage(query);
	// 将DO转换成DTO
	for (Cus_StateOneViewDO& sub : result)
	{
		auto dto = Cus_State_OneDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, mold, mold_method, frame, frame_method, time, time_method, number, number_method);
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, cost, cost_method, actual, actual_method, money, money_method, data, data_method);
		pages->addData(dto);
	}
	return pages;
}


Cus_State_AllpageDTO::Wrapper Cus_StateService::listAll(const Cus_StateQuery::Wrapper& query)
{
	//构建返回对象
	auto pages = Cus_State_AllpageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	//查询数据总条数
	Cus_StateDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;

	// 分页查询数据
	pages->total = count;
	pages->calcPages();
	list<Cus_StateAllViewDO> result = dao.selectAllWithPage(query);
	// 将DO转换成DTO
	for (Cus_StateAllViewDO& sub : result)
	{
		auto dto = Cus_State_AllDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, mold, mold_method, frame, frame_method, time, time_method, number, number_method);
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, cost, cost_method, actual, actual_method, money, money_method, data, data_method);
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, goods, goods_method, attr, attr_method, unit, unit_method, nums, nums_method);
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, dsc, dsc_method, total, total_method, tat, tat_method, tpt, tpt_method);
		pages->addData(dto);
	}
	return pages;
}