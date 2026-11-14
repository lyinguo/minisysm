#pragma once
#include"../DoInclude.h"
class CostDO :BaseDO
{
<<<<<<< HEAD
	//Ψһ��ʶ
    MYSQL_SYNTHESIZE(string, id, Id);
	//��������
	MYSQL_SYNTHESIZE(string, type, Type);
	//������
	MYSQL_SYNTHESIZE(string, class, Class);
	//����ʱ��
	MYSQL_SYNTHESIZE(string, time, Time);
	//������֧
	MYSQL_SYNTHESIZE(string, iet, Iet);
	//���
	MYSQL_SYNTHESIZE(double,money, Money);
	//��ע
	MYSQL_SYNTHESIZE(string, data, Data);
	//������
	MYSQL_SYNTHESIZE(double, settle, Settle);
	//����״̬
=======
	//唯一标识
    MYSQL_SYNTHESIZE(string, id, Id);
	//单据类型
	MYSQL_SYNTHESIZE(string, type, Type);
	//所属类
	MYSQL_SYNTHESIZE(string, class, Class);
	//单据时间
	MYSQL_SYNTHESIZE(string, time, Time);
	//所属收支
	MYSQL_SYNTHESIZE(string, iet, Iet);
	//金额
	MYSQL_SYNTHESIZE(double,money, Money);
	//备注
	MYSQL_SYNTHESIZE(string, data, Data);
	//结算金额
	MYSQL_SYNTHESIZE(double, settle, Settle);
	//结算状态
>>>>>>> remotes/origin/c6-v1.0-老凡夫俗子
	MYSQL_SYNTHESIZE(int, state, State);
public:
	CostDO() :BaseDO("Cost")
    {
		MYSQL_ADD_FIELD_PK("id", "s", Id);
		MYSQL_ADD_FIELD("type", "s", Type);
		MYSQL_ADD_FIELD("class", "s", Class);
		MYSQL_ADD_FIELD("datetime", "dt",DateTime);
		MYSQL_ADD_FIELD("iet", "s", Iet);
		MYSQL_ADD_FIELD("money", "d", Money);
		MYSQL_ADD_FIELD("data", "s", Data);
		MYSQL_ADD_FIELD("settle", "d", Settle);
		MYSQL_ADD_FIELD("state", "i", State);
    }
};
<<<<<<< HEAD
typedef std::shared_ptr<CostDO> PtrCostDO;
#endif // COST_DO_H
=======

typedef std::shared_ptr<CostDO> PtrCostDO;
>>>>>>> remotes/origin/c6-v1.0-老凡夫俗子
