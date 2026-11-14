#pragma once
#ifndef _ACCOUNTPAYABLEAGINGREPORTDTO_H
#define _ACCOUNTPAYABLEAGINGREPORTDTO_H
#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/*
应付账款明细表 — 单条记录 DTO
*/
class AccountPayableAgingReportDTO : public oatpp::DTO
{
    DTO_INIT(AccountPayableAgingReportDTO, DTO);
    // 客户（customer_name）
    DTO_FIELD(String,customer_name);
    DTO_FIELD_INFO(customer_name) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.customer_name");
    }
    // 单据类型（category）
    DTO_FIELD(String, category);
    DTO_FIELD_INFO(category) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.category");
    }
    // 所属组织（frame）
    DTO_FIELD(String, frame);
    DTO_FIELD_INFO(frame) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.frame");
    }
    // 单据时间(time)
    DTO_FIELD(String, time);
    DTO_FIELD_INFO(time) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.time");
    }
    // 单据编号(number)
    DTO_FIELD(String, number);
    DTO_FIELD_INFO(number) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.number");
    }
    // 增加应收款（cw）
    DTO_FIELD(Float64, cw);
    DTO_FIELD_INFO(cw) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.cw");
    }
    // 增加预付款（pia）
    DTO_FIELD(Float64, pia); 
    DTO_FIELD_INFO(pia) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.pia");
    }
    // 应收款余额（balance）
    DTO_FIELD(Float64, balance);
    DTO_FIELD_INFO(balance) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.balance");
    }
    // 备注 / data
    DTO_FIELD(String, data);
    DTO_FIELD_INFO(data) {
        info->description = ZH_WORDS_GETTER("account_payable_aging_report.field.data");
    }

};

/*
分页 DTO
*/
class AccountPayableAgingReportPageDTO : public PageDTO<AccountPayableAgingReportDTO::Wrapper>
{
    DTO_INIT(AccountPayableAgingReportPageDTO, PageDTO<AccountPayableAgingReportDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // _ACCOUNTPAYABLEAGINGREPORTDTO_H
