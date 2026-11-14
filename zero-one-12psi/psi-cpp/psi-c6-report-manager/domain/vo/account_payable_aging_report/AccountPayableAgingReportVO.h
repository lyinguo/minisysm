#pragma once
#ifndef _ACCOUNTPAYABLEAGINGREPORTVO_H
#define _ACCOUNTPAYABLEAGINGREPORTVO_H

#include "../../GlobalInclude.h"
#include "../../dto/account_payable_aging_report/AccountPayableAgingReportDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/*
应付账款明细表jsonvo，用于响应给客户端的Json对象
*/
class AccountPayableAgingReportVO : public JsonVO<AccountPayableAgingReportDTO::Wrapper>
{
    DTO_INIT(AccountPayableAgingReportVO, JsonVO<AccountPayableAgingReportDTO::Wrapper>);
};

/*
应付账款明细表报表分页jsonvo，用于响应给客户端的分页Json对象
*/
class AccountPayableAgingReportPageVO : public JsonVO<AccountPayableAgingReportPageDTO::Wrapper>
{
    DTO_INIT(AccountPayableAgingReportPageVO, JsonVO<AccountPayableAgingReportPageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_ACCOUNTPAYABLEAGINGREPORTVO_H