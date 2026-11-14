#include"stdafx.cpp"
#include"Cus_StateDAO.h"
#include"Cus_StateMapper.h"

inline std::string Cus_StateDAO::queryConditionBuilder(const Cus_StateQuery::Wrapper& query, SqlParams& params)
{
    stringstream sqlCondition;
    sqlCondition << "where 1=1 ";
    if (query->name)
    {
        sqlCondition << " and bi.`customer`=? ";
        SQLPARAMS_PUSH(params, "s", std::string, query->name.getValue(""));
    }
    //起始时间
    if (query->starttime)
    {
        sqlCondition << " and br.`time`>=? ";
        SQLPARAMS_PUSH(params, "dt", std::string, query->starttime.getValue(""));
    }
    //结束时间
    if (query->endtime)
    {
        sqlCondition << " and br.`time`<=? ";
        SQLPARAMS_PUSH(params, "dt", std::string, query->endtime.getValue(""));
    }
    return sqlCondition.str();
}

uint64_t Cus_StateDAO::count(const Cus_StateQuery::Wrapper& query)
{
    SqlParams params;
    if (query->is_detail)           //明细
    {
        string sql = R"(
        select count(bi.`number`)
        from bill_info bio
        left join bill bi on bio.`pid`=bi.`id`
        left join bre br on br.`number`=bi.`number`
        left join bor bo on bo.`number`=br.`number`
        left join bor_info brio on brio.`pid`=bo.`id`
        )";
        sql += queryConditionBuilder(query, params);
        return sqlSession->executeQueryNumerical(sql, params);
    }
    else        //不明晰
    {
        string sql = R"(
        select count(bi.`number`)
        from bill_info bio
        left join bill bi on bio.`pid`=bi.`id`
        left join bre br on br.`number`=bi.`number`
        )";
        sql += queryConditionBuilder(query, params);
        return sqlSession->executeQueryNumerical(sql, params);
    }
}

std::list<Cus_StateOneViewDO> Cus_StateDAO::selectOneWithPage(const Cus_StateQuery::Wrapper& query)
{
    SqlParams params;
    string sql = R"(
    select 
    bio.`mold` ,br.`frame` ,br.`time`,
    br.`number` ,br.`cost` ,br.`actual`,
    br.`money` ,br.`data` 
    from bill_info bio
    left join bill bi on bio.`pid`=bi.`id`
    left join bre br on br.`number`=bi.`number`
    )";
    // 构建查询条件
    sql += queryConditionBuilder(query, params);
    // 构建排序语句
    sql += " ORDER BY br.`time` DESC ";
    // 构建分页条件
    sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

    // 执行查询
    return sqlSession->executeQuery<Cus_StateOneViewDO>(sql, Cus_StateOneMapper(), params);
}

std::list<Cus_StateAllViewDO> Cus_StateDAO::selectAllWithPage(const Cus_StateQuery::Wrapper& query)
{
    SqlParams params;
    string sql = R"(
    select 
    bio.`mold` ,br.`frame` ,br.`time`,
    br.`number` ,br.`cost` ,br.`actual`,
    br.`money` ,br.`data` ,brio.`goods` ,brio.`attr`,
    brio.`unit` ,brio.`nums` ,brio.`dsc`,
    brio.`total` ,brio.`tat` ,brio.`tpt`
    from bill_info bio
    left join bill bi on bio.`pid`=bi.`id`
    left join bre br on br.`number`=bi.`number`
    left join bor bo on bo.`number`=br.`number`
    left join bor_info brio on brio.`pid`=bo.`id`
    )";
    // 构建查询条件
    sql += queryConditionBuilder(query, params);
    // 构建排序语句
    sql += " ORDER BY br.`time` DESC ";
    // 构建分页条件
    sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

    // 执行查询
    return sqlSession->executeQuery<Cus_StateAllViewDO>(sql, Cus_StateAllMapper(), params);
}
