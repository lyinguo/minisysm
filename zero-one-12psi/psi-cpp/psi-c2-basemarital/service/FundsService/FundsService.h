#pragma once

#ifndef _FUNDSER_H_
#define _FUNDSER_H_

#include"domain/vo/FundsVO/FundsVO.h"
#include"domain/dto/FundsDTO/FundsDTO.h"
#include"domain/query/FundsQuery/FundsQuery.h"


class FundsService
{
public:
//??????
	AccountDetailDTO::Wrapper getAccountById(std::string id);
//???????
	std::string saveNewAccount(AddAccountDTO::Wrapper dto);
//??????
	bool updateAccount(AccountDetailDTO::Wrapper dto);
// ???
	bool deleteFunds(const oatpp::List<oatpp::String>& ids);
// ?????????
	FundsPageDTO::Wrapper listFunds(const FundsQuery::Wrapper& query);
};


#endif // !_FUNDSER_H_
