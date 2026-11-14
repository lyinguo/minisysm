#pragma once

#ifndef _FUNDSDAO_H_
#define _FUNDSDAO_H_
#include"BaseDAO.h"
#include"../../domain/do/AccountDO.h"
#include"domain/query/FundsQuery/FundsQuery.h"

class AccountDAO : public BaseDAO
{
public:
//id��ѯaccount���������
	PtrAccountDO selectById(std::string id);
//����account���������
	int updateAccount(const AccountDO& newAccount);
//��account��������µ�����
	int insertAccount(const AccountDO& newAccount);
// ��ҳ��ѯ
	uint64_t count(const FundsQuery::Wrapper& query);
	std::list<AccountDO> selectWithPage(const FundsQuery::Wrapper& query);
};


#endif // !_FUNDSDAO_H_
