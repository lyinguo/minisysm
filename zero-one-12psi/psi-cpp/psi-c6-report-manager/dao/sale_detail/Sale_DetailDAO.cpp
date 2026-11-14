#include"stdafx.cpp"
#include"Sale_DetailDAO.h"
#include"Sale_DetailMapper.h"


std::string Sale_DetailDAO::queryConditionBuilder(const Sale_DetailQuery::Wrapper& query, SqlParams& params)
{
    stringstream sqlCondition;
    sqlCondition << "where 1=1 ";
    //客户名称
    if (query->name)
    {
        sqlCondition << " and b.`customer`=? ";
        SQLPARAMS_PUSH(params, "s", std::string, query->name.getValue(""));
    }
    //商品名称
    if (query->object)
    {
        sqlCondition << " and boi.`goods`=? ";
        SQLPARAMS_PUSH(params, "s", std::string, query->object.getValue(""));
    }
    //仓库
    if (query->warehouse)
    {
        sqlCondition << " and boi.`warehouse`=? ";
        SQLPARAMS_PUSH(params, "s", std::string, query->warehouse.getValue(""));
    }
    //起始时间
    if (query->starttime)
    {
        sqlCondition << " and b.`time`>=? ";
        SQLPARAMS_PUSH(params, "dt", std::string, query->starttime.getValue(""));
    }
    //结束时间
    if (query->endtime)
    {
        sqlCondition << " and b.`time`<=? ";
        SQLPARAMS_PUSH(params, "dt", std::string, query->endtime.getValue(""));
    }
    //单据类型
    if (query->type)
    {
        sqlCondition << " and bi.`mold`=? ";
        SQLPARAMS_PUSH(params, "s", std::string, query->type.getValue(""));
    }
    //备注信息
    if (query->data)
    {
        sqlCondition << " and boi.`data`=? ";
        SQLPARAMS_PUSH(params, "s", std::string, query->data.getValue(""));
    }
    return sqlCondition.str();
}

uint64_t Sale_DetailDAO::count(const Sale_DetailQuery::Wrapper& query)
{
    SqlParams params;
    string sql = R"(
    select count(b.`number`)
    FROM bill_info bi 
    LEFT JOIN bill b ON bi.`pid` = b.`id`
    LEFT JOIN bor bo ON b.`number` = bo.`number`
    LEFT JOIN bor_info boi ON boi.`pid` = bo.`id`
    )";
    sql += queryConditionBuilder(query, params);
    return sqlSession->executeQueryNumerical(sql, params);
}

std::list<Sale_DetailViewDO> Sale_DetailDAO::selectWithPage(const Sale_DetailQuery::Wrapper& query)
{
    SqlParams params;
    string sql = R"(
    SELECT
    bi.`mold`, b.`frame`, b.`customer`,
    b.`time`, b.`number`, boi.`goods`,
    boi.`attr`, boi.`warehouse`, boi.`unit`,
    boi.`price`, boi.`nums`, boi.`dsc`,
    boi.`total`, boi.`tat`, boi.`tpt`,
    boi.`data`
    FROM bill_info bi 
    LEFT JOIN bill b ON bi.`pid` = b.`id`
    LEFT JOIN bor bo ON b.`number` = bo.`number`
    LEFT JOIN bor_info boi ON boi.`pid` = bo.`id`
    )";
    // 构建查询条件
    sql += queryConditionBuilder(query, params);
    // 构建排序语句
    sql += " ORDER BY b.`time` DESC ";
    // 构建分页条件
    sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

    // 执行查询
    return sqlSession->executeQuery<Sale_DetailViewDO>(sql, Sale_DetailMapper(), params);
}
