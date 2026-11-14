#include "stdafx.h"
#include "InventoryBalanceReportService.h"
#include "../../dao/inventory_balance_report/InventoryBalanceReportDAO.h"
#include <map>
#include <unordered_map>
#include <vector>
#include <algorithm>

/**
 * 分页查询商品库存余额报表
 * 说明：
 * - 调用 DAO 层的 selectWithPage 方法获取数据（每个仓库-商品一行）
 * - 按商品分组，将仓库数据聚合成列表
 * - 将 DO 对象转换为 DTO 对象
 * - 封装为分页 DTO 返回
 */

InventoryBalanceReportPageDTO::Wrapper InventoryBalanceReportService::listAll(const InventoryBalanceReportQuery::Wrapper& query)
{
	auto pages = InventoryBalanceReportPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	InventoryBalanceReportDAO dao;
	
	// 获取所有数据，格式是 商品信息-仓库信息-仓库数据信息。其中商品信息存在大量冗余，这里面临着和应付款明细表一样的优化问题。
	std::list<InventoryBalanceReportViewDOPtr> result = dao.selectWithPage(query);	//返回的是视图DO
	
	// 如果没有数据，直接返回
	if (result.empty()) {
		pages->total = v_int64(0);
		pages->pages = v_int64(0);
		return pages;
	}

	// 按商品分组：使用商品编号作为key（因为商品编号应该唯一）
	// 结构：map<商品编号, {商品信息, 仓库列表}>
	std::unordered_map<std::string, InventoryBalanceReportDTO::Wrapper> productMap;
	
	for (InventoryBalanceReportViewDOPtr& item : result) {
		// 安全检查：跳过空指针
		if (!item) {
			continue;
		}
		
		std::string productNumber = item->getNumber().empty() ? "" : item->getNumber();
		
		// 如果该商品不存在，创建新的DTO
		if (productMap.find(productNumber) == productMap.end()) {
			auto dto = InventoryBalanceReportDTO::createShared();
			
			// 设置商品基本信息 这里应该不能直接访问进行赋值，可能是private
			// item是视图DO的一条数据
			dto->number = item->getNumber();
			dto->name = item->getName();
			dto->unit = item->getUnit();
			
			// 初始化仓库列表
			dto->room = oatpp::Vector<InventoryRoomDTO::Wrapper>::createShared();
			
			productMap[productNumber] = dto;
		}
		
		// 创建仓库信息DTO并添加到该商品的仓库列表
		auto roomDto = InventoryRoomDTO::createShared();
		
		// 设置仓库名称（需要检查空指针，避免解引用空指针）
		if (auto warehouseNamePtr = item->getWarehouseNamePtr()) {
			roomDto->warehouse_name = *warehouseNamePtr;
		}
		// 设置成本（直接使用值方法，与其他数值字段保持一致）
		roomDto->cost = item->getCost();
		roomDto->qty = item->getQty();
		roomDto->total_cost = item->getTotalCost();
		
		// 安全检查：确保productMap中有该商品且room列表存在
		if (productMap.find(productNumber) != productMap.end() && productMap[productNumber] && productMap[productNumber]->room) {
			productMap[productNumber]->room->push_back(roomDto);
		}
	}
	
	// 为每个商品计算汇总数据并插入到room列表的第0个位置
	for (auto& pair : productMap) {
		auto dto = pair.second;
		if (!dto) {
			continue; // 跳过空指针
		}
		if (dto->room && dto->room->size() > 0) {
			// 计算汇总数据：所有仓库的合计
			double totalQty = 0.0;
			double totalCost = 0.0;
			
			for (auto& room : *dto->room) {
				if (!room) {
					continue; // 跳过空指针
				}
				totalQty += room->qty ? *room->qty : 0.0;
				totalCost += room->total_cost ? *room->total_cost : 0.0;
			}
			
			// 计算平均成本（汇总成本 = 总成本 / 总数量）
			double summaryPrice = (totalQty != 0.0) ? (totalCost / totalQty) : 0.0;
			
			// 创建汇总DTO（0号位置）
			auto summaryRoomDto = InventoryRoomDTO::createShared();
			summaryRoomDto->warehouse_name = oatpp::String("sum_warehouse");  // 汇总标识
			summaryRoomDto->cost = summaryPrice;
			summaryRoomDto->qty = totalQty;
			summaryRoomDto->total_cost = totalCost;
			
			// 在列表开头插入汇总数据（0号位置）
			dto->room->insert(dto->room->begin(), summaryRoomDto);
		}
	}
	
	// 获取商品总数（用于分页计算）
	uint64_t totalProducts = dao.count(query);
	pages->total = v_int64(totalProducts);
	
	// 将分组后的数据转换为有序列表（按商品编号排序，保持一致性）
	std::vector<std::pair<std::string, InventoryBalanceReportDTO::Wrapper>> sortedProducts;
	for (auto& pair : productMap) {
		sortedProducts.push_back(pair);
	}
	// 按商品编号排序
	std::sort(sortedProducts.begin(), sortedProducts.end(), 
		[](const std::pair<std::string, InventoryBalanceReportDTO::Wrapper>& a, 
		   const std::pair<std::string, InventoryBalanceReportDTO::Wrapper>& b) {
			return a.first < b.first;
		});
	
	// 添加当前页的商品数据（已由DAO层分页，这里直接添加即可）
	for (auto& pair : sortedProducts) {
		if (pair.second) {
			pages->addData(pair.second);
		}
	}
	
	// 计算总页数
	//pages->calcPages();

	return pages;
}
