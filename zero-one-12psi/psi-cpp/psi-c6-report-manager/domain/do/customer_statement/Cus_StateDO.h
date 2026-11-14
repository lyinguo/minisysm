#pragma once
#include "../DoInclude.h"
class Cus_StateDO :public BaseDO
{
	MYSQL_SYNTHESIZE(string, id, id_method);
	MYSQL_SYNTHESIZE(string, mold, mold_method);
public:
	Cus_StateDO() :BaseDO("bill_info")
	{
		MYSQL_ADD_FIELD_PK("id", "s", id);
		MYSQL_ADD_FIELD("mold", "s", mold);
	}
};

class Cus_StateOneViewDO :public Cus_StateDO
{
	//所属组织  
	MYSQL_SYNTHESIZE(string, frame, frame_method);
	//单据时间 
	MYSQL_SYNTHESIZE(string, time, time_method);
	//单据编号  
	MYSQL_SYNTHESIZE(string, number, number_method);
	//优惠金额
	MYSQL_SYNTHESIZE(double, cost, cost_method);
	//应收金额
	MYSQL_SYNTHESIZE(double, actual, actual_method);
	//实收金额
	MYSQL_SYNTHESIZE(double, money, money_method);
	//备注  data
	MYSQL_SYNTHESIZE(string, data, data_method);
};


//隐藏明细的智能指针
typedef std::shared_ptr<Cus_StateOneViewDO> PtrCus_StateOneViewDO;


class Cus_StateAllViewDO :public Cus_StateDO
{
	//所属组织  
	MYSQL_SYNTHESIZE(string, frame, frame_method);
	//单据时间 
	MYSQL_SYNTHESIZE(string, time, time_method);
	//单据编号  
	MYSQL_SYNTHESIZE(string, number, number_method);
	//优惠金额
	MYSQL_SYNTHESIZE(double, cost, cost_method);
	//应收金额
	MYSQL_SYNTHESIZE(double, actual, actual_method);
	//实收金额
	MYSQL_SYNTHESIZE(double, money, money_method);
	//备注  data
	MYSQL_SYNTHESIZE(string, data, data_method);
	//名称
	MYSQL_SYNTHESIZE(string, goods, goods_method);
	//属性
	MYSQL_SYNTHESIZE(string, attr, attr_method);
	//单位
	MYSQL_SYNTHESIZE(string, unit, unit_method);
	//数量
	MYSQL_SYNTHESIZE(int, nums, nums_method);
	//折扣额
	MYSQL_SYNTHESIZE(double, dsc, dsc_method);
	//金额
	MYSQL_SYNTHESIZE(double, total, total_method);
	//税额
	MYSQL_SYNTHESIZE(double, tat, tat_method);
	//价税合计
	MYSQL_SYNTHESIZE(double, tpt, tpt_method);
};

typedef std::shared_ptr<Cus_StateAllViewDO> PtrCus_StateAllViewDO;