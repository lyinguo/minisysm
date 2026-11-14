#pragma once
#ifndef _INVENTORYBALANCEREPORTDTO_H
#define _INVENTORYBALANCEREPORTDTO_H
#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)


/*
仓库信息 DTO
表示每个仓库的库存信息（成本、数量、总成本）
*/

class InventoryRoomDTO : public oatpp::DTO {
  DTO_INIT(InventoryRoomDTO, DTO);

  // 仓库名称
  DTO_FIELD(String, warehouse_name);
  DTO_FIELD_INFO(warehouse_name) {
    info->description = ZH_WORDS_GETTER("inventory_balance_report.field.warehouse_name");
  }
  
  // 成本（平均成本=总成本/数量）
  DTO_FIELD(Float64, cost);
  DTO_FIELD_INFO(cost) {
    info->description = ZH_WORDS_GETTER("inventory_balance_report.field.cost");
  }

  // 数量
  DTO_FIELD(Float64, qty);
  DTO_FIELD_INFO(qty) {
    info->description = ZH_WORDS_GETTER("inventory_balance_report.field.qty");
  }

  // 总成本
  DTO_FIELD(Float64, total_cost);
  DTO_FIELD_INFO(total_cost) {
    info->description = ZH_WORDS_GETTER("inventory_balance_report.field.total_cost");
  }

};





/*
库存结余报表 — 单条记录 DTO
匹配Excel报表结构：按商品分组，每个商品有多个仓库的横向展开（成本、数量、总成本）+汇总字段
支持动态数量的仓库（使用列表）
*/
class InventoryBalanceReportDTO : public oatpp::DTO {
  DTO_INIT(InventoryBalanceReportDTO, DTO);
  
  // 商品名称
  DTO_FIELD(String, name);
  DTO_FIELD_INFO(name) {
    info->description = ZH_WORDS_GETTER("inventory_balance_report.field.good_name");
  }


  // 商品编号
  DTO_FIELD(String, number);
  DTO_FIELD_INFO(number) {
    info->description = ZH_WORDS_GETTER("inventory_balance_report.field.good_number");
  }

  
  // 单位
  DTO_FIELD(String, unit);
  DTO_FIELD_INFO(unit) {
    info->description = ZH_WORDS_GETTER("inventory_balance_report.field.good_unit");
  }
  
  // 仓库信息列表（动态数量，支持所有仓库）
  DTO_FIELD(Vector<InventoryRoomDTO::Wrapper>, room);
  DTO_FIELD_INFO(room) { info->description = ZH_WORDS_GETTER("inventory_balance_report.field.room"); }
 
};

/*
分页 DTO（用于返回分页结果）
*/
class InventoryBalanceReportPageDTO : public PageDTO<InventoryBalanceReportDTO::Wrapper> {
  DTO_INIT(InventoryBalanceReportPageDTO, PageDTO<InventoryBalanceReportDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // _INVENTORYBALANCEREPORTDTO_H
