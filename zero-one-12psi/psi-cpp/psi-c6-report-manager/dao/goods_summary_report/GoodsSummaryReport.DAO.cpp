#include "GoodsSummaryReportDAO.h"
#include "stdafx.h"
#include "GoodsSummaryReportMapper.h"
/*
@author: WEI伦
@date: 2025/10/26
*/

std::list<PtrGoodSummaryReportViewDO> GoodsSummaryReportDAO::selectWithPage(const GoodsSummaryReportQuery::Wrapper& query) {
	stringstream sql;
	SqlParams params;

	sql << R"(
		SELECT
			goods.name,
			warehouse.name as warehouse,
			goods.number,
			goods.spec,
			goods.unit,

			-- 汇总
			IFNULL(buy_info.uns, 0) + IFNULL(sre_info.uns, 0) + IFNULL(entry_info.uns, 0) + IFNULL(swap_enter_info.uns, 0)
			- IFNULL(bre_info.uns, 0) - IFNULL(sell_info.uns, 0) - IFNULL(extry_info.uns, 0) - IFNULL(swap_out_info.uns, 0) as sum_uns,
			IFNULL(buy_info.bct, 0) + IFNULL(sre_info.bct, 0) + IFNULL(entry_info.bct, 0) + IFNULL(swap_enter_info.bct, 0)
			- IFNULL(bre_info.bct, 0) - IFNULL(sell_info.bct, 0) - IFNULL(extry_info.bct, 0) - IFNULL(swap_out_info.bct, 0) as sum_bct,
			0 as sum_uct,

			-- 期初数据（通过room_info计算期初库存）
			IFNULL(room_state.uct, 0) as state_uct,
			IFNULL(room_state.uns, 0) as state_uns,
			IFNULL(room_state.bct, 0) as state_bct,

			-- 采购单数据
			IFNULL(buy_info.uct, 0) as buy_uct,
			IFNULL(buy_info.uns, 0) as buy_uns,
			IFNULL(buy_info.bct, 0) as buy_bct,

			-- 采购退货单据
			IFNULL(bre_info.uct, 0) as bre_uct,
			IFNULL(bre_info.uns, 0) as bre_uns,
			IFNULL(bre_info.bct, 0) as bre_bct,

			-- 销售单据
			IFNULL(sell_info.uct, 0) as sell_uct,
			IFNULL(sell_info.uns, 0) as sell_uns,
			IFNULL(sell_info.bct, 0) as sell_bct,

			-- 销售退货单据
			IFNULL(sre_info.uct, 0) as sre_uct,
			IFNULL(sre_info.uns, 0) as sre_uns,
			IFNULL(sre_info.bct, 0) as sre_bct,

			-- 调拨出
			IFNULL(swap_out_info.uct, 0) as swap_out_uct,
			IFNULL(swap_out_info.uns, 0) as swap_out_uns,
			IFNULL(swap_out_info.bct, 0) as swap_out_bct,

			-- 调拨入
			IFNULL(swap_enter_info.uct, 0) as swap_enter_uct,
			IFNULL(swap_enter_info.uns, 0) as swap_enter_uns,
			IFNULL(swap_enter_info.bct, 0) as swap_enter_bct,

			-- 其它入
			IFNULL(entry_info.uct, 0) as entry_uct,
			IFNULL(entry_info.uns, 0) as entry_uns,
			IFNULL(entry_info.bct, 0) as entry_bct,

			-- 其它出
			IFNULL(extry_info.uct, 0) as extry_uct,
			IFNULL(extry_info.uns, 0) as extry_uns,
			IFNULL(extry_info.bct, 0) as extry_bct
		FROM goods
		LEFT JOIN room ON goods.id = room.goods
		LEFT JOIN warehouse ON room.warehouse = warehouse.id )";
	buildBusinessJoin(query, params, sql, "buy", "buy_info");
	buildBusinessJoin(query, params, sql, "bre", "bre_info");
	buildBusinessJoin(query, params, sql, "sell", "sell_info");
	buildBusinessJoin(query, params, sql, "sre", "sre_info");
	buildBusinessJoin(query, params, sql, "entry", "entry_info");
	buildBusinessJoin(query, params, sql, "extry", "extry_info");
	buildSwapJoin(query, params, sql);
	buildRoomStateJoin(query, params, sql);

	// 添加查询条件
	string whereClause = queryConditionBuilder(query, params);
	sql << whereClause;

	// 添加分页
	if (query->pageIndex && query->pageSize) {
		int pageIndex = query->pageIndex.getValue(1);
		int pageSize = query->pageSize.getValue(20);
		int offset = (pageIndex - 1) * pageSize;

		sql << " LIMIT ?, ?";
		SQLPARAMS_PUSH(params, "i", int, offset);
		SQLPARAMS_PUSH(params, "i", int, pageSize);
	}

	cout << "=====sql查询语句=====" << endl << sql.str() << endl << "====================" << endl;
	// 执行查询结果
	return sqlSession->executeQuery<PtrGoodSummaryReportViewDO>(sql.str(), GoodsSummaryReportMapper(), params);
}



//构建业务数据链接
void GoodsSummaryReportDAO::buildBusinessJoin(const GoodsSummaryReportQuery::Wrapper& query, SqlParams& params, stringstream& sqlCondition, const string& table, const
	string& target) {
	sqlCondition
		<< "LEFT JOIN ("
		<< "    SELECT"
		<< "        info.goods,"
		<< "        info.warehouse,"
		<< "        IFNULL(SUM(info.price * info.nums) / NULLIF(SUM(info.nums), 0), 0) AS uct,"
		<< "        SUM(info.nums) AS uns,"
		<< "        SUM(info.price * info.nums) AS bct "
		<< "    FROM " << table << "_info info "
		<< "    INNER JOIN " << table << " main ON main.id = info.pid";

	// 添加时间过滤条件到子查询内部
	if (query->startTime && !query->startTime.getValue("").empty() ||
		query->endTime && !query->endTime.getValue("").empty()) {
		sqlCondition << " WHERE 1=1";
		if (query->startTime && !query->startTime.getValue("").empty()) {
			sqlCondition << " AND main.time >= ?";
			SQLPARAMS_PUSH(params, "s", std::string, query->startTime.getValue(""));
		}
		if (query->endTime && !query->endTime.getValue("").empty()) {
			sqlCondition << " AND main.time <= ?";
			SQLPARAMS_PUSH(params, "s", std::string, query->endTime.getValue(""));
		}
	}

	sqlCondition
		<< "    GROUP BY info.goods, info.warehouse"
		<< ") " << target << " ON goods.id = " << target << ".goods "
		<< "    AND room.warehouse = " << target << ".warehouse ";
}

/*
	构建调拨信息数据链接
	访问数据库中swap和swap_info表
*/
void GoodsSummaryReportDAO::buildSwapJoin(const GoodsSummaryReportQuery::Wrapper& query, SqlParams& params, stringstream& sqlCondition) {
	sqlCondition
		<< "LEFT JOIN ("
		<< "  SELECT "
		<< "    goods, "
		<< "    warehouse, "
		<< "    IFNULL(SUM(price * nums) / NULLIF(SUM(nums), 0), 0) as uct, "
		<< "    SUM(nums) as uns, "
		<< "    SUM(price * nums) as bct "
		<< "  FROM swap_info "
		<< "  INNER JOIN swap ON swap.id = swap_info.pid ";
	// 添加时间过滤条件到子查询内部
	if (query->startTime && !query->startTime.getValue("").empty() ||
		query->endTime && !query->endTime.getValue("").empty()) {
		sqlCondition << " WHERE 1=1";
		if (query->startTime && !query->startTime.getValue("").empty()) {
			sqlCondition << " AND swap.time >= ?";
			SQLPARAMS_PUSH(params, "s", std::string, query->startTime.getValue(""));
		}
		if (query->endTime && !query->endTime.getValue("").empty()) {
			sqlCondition << " AND swap.time <= ?";
			SQLPARAMS_PUSH(params, "s", std::string, query->endTime.getValue(""));
		}
	}
	sqlCondition
		<< "  GROUP BY swap_info.goods,swap_info.warehouse "
		<< ") swap_out_info ON goods.id = swap_out_info.goods "
		<< "  AND room.warehouse = swap_out_info.warehouse ";


	sqlCondition
		<< "LEFT JOIN ("
		<< "  SELECT "
		<< "    goods, "
		<< "    storehouse as warehouse, "
		<< "    IFNULL(SUM(price * nums) / NULLIF(SUM(nums), 0), 0) as uct, "
		<< "    SUM(nums) as uns, "
		<< "    SUM(price * nums) as bct "
		<< "  FROM swap_info "
		<< "  INNER JOIN swap ON swap.id = swap_info.pid ";
	// 添加时间过滤条件到子查询内部
	if (query->startTime && !query->startTime.getValue("").empty() ||
		query->endTime && !query->endTime.getValue("").empty()) {
		sqlCondition << " WHERE 1=1";
		if (query->startTime && !query->startTime.getValue("").empty()) {
			sqlCondition << " AND swap.time >= ?";
			SQLPARAMS_PUSH(params, "s", std::string, query->startTime.getValue(""));
		}
		if (query->endTime && !query->endTime.getValue("").empty()) {
			sqlCondition << " AND swap.time <= ?";
			SQLPARAMS_PUSH(params, "s", std::string, query->endTime.getValue(""));
		}
	}
	sqlCondition
		<< "  GROUP BY swap_info.goods,swap_info.storehouse "
		<< ") swap_enter_info ON goods.id = swap_enter_info.goods "
		<< "  AND room.warehouse = swap_enter_info.warehouse ";
}
/*
	构建期初信息数据链接
	通过访问数据库中room,room_info以及startTime参数确认。
*/
void GoodsSummaryReportDAO::buildRoomStateJoin(const GoodsSummaryReportQuery::Wrapper& query, SqlParams& params, stringstream& sqlCondition) {
	sqlCondition
		<< "LEFT JOIN ( "
		<< "  SELECT "
		<< "    room.goods, room.warehouse, "
		<< "    IFNULL(SUM(CASE WHEN room_info.direction = 1 THEN room_info.price * room_info.nums ELSE 0 END) /NULLIF(SUM(CASE WHEN room_info.direction = 1 THEN room_info.nums ELSE 0 END), 0), 0) as uct, "
		<< "    SUM(CASE WHEN room_info.direction = 1 THEN room_info.nums ELSE 0 END) - SUM(CASE WHEN room_info.direction = 0 THEN room_info.nums ELSE 0 END) as uns, "
		<< "    SUM(CASE WHEN room_info.direction = 1 THEN room_info.price * room_info.nums ELSE 0 END) - SUM(CASE WHEN room_info.direction = 0 THEN room_info.price * room_info.nums ELSE 0 END) as bct "
		<< "  FROM room_info "
		<< "  INNER JOIN room ON room_info.pid = room.id ";

	//如果有初始时间则期初表示起始时间之前的仓库情况，否则期初则为0
	if (query->startTime && !query->startTime.getValue("").empty()) {
		sqlCondition << " WHERE room_info.time < ?";
		SQLPARAMS_PUSH(params, "s", std::string, query->startTime.getValue(""));
	}
	else {
		sqlCondition << " WHERE 1=0 ";
	}
		
	sqlCondition
		<< "  GROUP BY room.goods, room.warehouse"
		<< ") room_state ON goods.id = room_state.goods AND room.warehouse = room_state.warehouse ";
}


/*
	添加goods(商品名），warehouse(仓库列表)参数条件
*/
std::string GoodsSummaryReportDAO::queryConditionBuilder(const GoodsSummaryReportQuery::Wrapper& query, SqlParams& params) {
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";

	// 商品名称筛选
	if (query->goods && !query->goods.getValue("").empty()) {
		sqlCondition << " AND goods.name LIKE ?";
		std::string goodsParam = "%" + query->goods.getValue("") + "%";
		SQLPARAMS_PUSH(params, "s", std::string, goodsParam);
	}

	//// 仓库筛选
	//if (query->warehouse && !query->warehouse.get()->empty()) {
	//	sqlCondition << " AND warehouse.name IN (";
	//	auto warehouseList = query->warehouse.get();
	//	for (size_t i = 0; i < warehouseList->size(); ++i) {
	//		if (i > 0) sqlCondition << ",";
	//		sqlCondition << "?";
	//		SQLPARAMS_PUSH(params, "s", std::string, warehouseList[i]);
	//	}
	//	sqlCondition << ")";
	//}

	return sqlCondition.str();
}


uint64_t GoodsSummaryReportDAO::getCount(const GoodsSummaryReportQuery::Wrapper& query)
{
	SqlParams params;
	stringstream sql;
	sql << R"(
		SELECT COUNT(*)
		FROM goods
		LEFT JOIN room ON goods.id = room.goods
		LEFT JOIN warehouse ON room.warehouse = warehouse.id )";
	buildBusinessJoin(query, params, sql, "buy", "buy_info");
	buildBusinessJoin(query, params, sql, "bre", "bre_info");
	buildBusinessJoin(query, params, sql, "sell", "sell_info");
	buildBusinessJoin(query, params, sql, "sre", "sre_info");
	buildBusinessJoin(query, params, sql, "entry", "entry_info");
	buildBusinessJoin(query, params, sql, "extry", "extry_info");
	buildSwapJoin(query, params, sql);
	buildRoomStateJoin(query, params, sql);

	// 添加查询条件
	string whereClause = queryConditionBuilder(query, params);
	sql << whereClause;

	cout << "=====sql查询语句=====" << endl << sql.str() << endl << "====================" << endl;
	// 返回查询结果
	return sqlSession->executeQueryNumerical(sql.str(), params);
}