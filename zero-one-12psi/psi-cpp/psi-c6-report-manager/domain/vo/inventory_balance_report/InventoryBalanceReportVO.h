#pragma once
#ifndef _INVENTORYBALANCEREPORTVO_H
#define _INVENTORYBALANCEREPORTVO_H

#include "../../GlobalInclude.h"
#include "../../dto/inventory_balance_report/InventoryBalanceReportDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/*
库存余额报表jsonvo，用于响应给客户端的Json对象
*/
class InventoryBalanceReportVO : public JsonVO<InventoryBalanceReportDTO::Wrapper>
{
    DTO_INIT(InventoryBalanceReportVO, JsonVO<InventoryBalanceReportDTO::Wrapper>);
};

/*
库存余额报表分页jsonvo，用于响应给客户端的分页Json对象
*/
class InventoryBalanceReportPageVO : public JsonVO<InventoryBalanceReportPageDTO::Wrapper>
{
    DTO_INIT(InventoryBalanceReportPageVO, JsonVO<InventoryBalanceReportPageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_INVENTORYBALANCEREPORTVO_H