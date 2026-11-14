#include"stdafx.h"
#include"FundsDAO.h"
#include"FundsMapper.h"
#include <sstream>

static std::string fundsQueryConditionBuilder(const FundsQuery::Wrapper& query, SqlParams& params)
{
	std::stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->name)
	{
		sqlCondition << " AND `accountname` LIKE CONCAT('%',?,'%')";
		SQLPARAMS_PUSH(params, "s", std::string, query->name.getValue(""));
	}
	if (query->number)
	{
		sqlCondition << " AND `accountnumber` LIKE CONCAT('%',?,'%')";
		SQLPARAMS_PUSH(params, "s", std::string, query->number.getValue(""));
	}
	if (query->data)
	{
		sqlCondition << " AND `data` LIKE CONCAT('%',?,'%')";
		SQLPARAMS_PUSH(params, "s", std::string, query->data.getValue(""));
	}
	return sqlCondition.str();
}

uint64_t AccountDAO::count(const FundsQuery::Wrapper& query)
{
	SqlParams params;
	std::string sql = "SELECT COUNT(*) FROM account";
	sql += fundsQueryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<AccountDO> AccountDAO::selectWithPage(const FundsQuery::Wrapper& query)
{
	SqlParams params;
	std::string sql = "SELECT id,accountname,accountnumber,frame,time,initial,balance,data FROM account";
	sql += fundsQueryConditionBuilder(query, params);
	sql += " ORDER BY `id` DESC";
	sql += " LIMIT " + std::to_string((query->pageIndex - 1) * query->pageSize) + "," + std::to_string(query->pageSize);
	return sqlSession->executeQuery<AccountDO>(sql, AccountMapper(), params);
}

/*
�˻�id
MYSQL_SYNTHESIZE(string, id, Id);
�˻�����
MYSQL_SYNTHESIZE(string, accountname, Accountname);
�˻����
MYSQL_SYNTHESIZE(string, accountnumber, Accountnumber);
������֯
MYSQL_SYNTHESIZE(string, frame, Frame);
�������
MYSQL_SYNTHESIZE(string, time, Time);
�ڳ����
MYSQL_SYNTHESIZE(double, initial, Initial);
�˻����
MYSQL_SYNTHESIZE(double, balance, Balance);
��ע��Ϣ
MYSQL_SYNTHESIZE(string, data, Data);
*/
PtrAccountDO AccountDAO::selectById(std::string id)
{
	string sql = "SELECT id,accountname,accountnumber,frame,time,initial,balance,data FROM account WHERE `id`=?";
	return sqlSession->executeQueryOne<PtrAccountDO>(sql, PtrAccountMapper(), "%s", id);
}
//����account���������
int AccountDAO::updateAccount(const AccountDO& newAccount)
{
	std::string sql = "UPDATE account SET `accountname`=?,`accountnumber`=?,`frame`=?,`time`=?,`initial`=?,`balance`=?,`data`=? WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%f%f%s%s", newAccount.getAccountname(), newAccount.getAccountnumber(), newAccount.getFrame(), \
		newAccount.getTime(), newAccount.getInitial(), newAccount.getBalance(), newAccount.getData(), newAccount.getId());
}
//��account��������µ�����
int AccountDAO::insertAccount(const AccountDO& newAccount)
{
	std::string sql = "INSERT INFO account (`id`,`accountname`,`accountnumber`,`frame`,`time`,`initial`,`balance`,`data`) VALUES (?,?,?,?,?,?,?,?)";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%f%f%s", newAccount.getId(), newAccount.getAccountname(), \
		newAccount.getAccountnumber(), newAccount.getFrame(), newAccount.getTime(), newAccount.getInitial(), newAccount.getBalance(), newAccount.getData());
}
//��account����ɾ������
