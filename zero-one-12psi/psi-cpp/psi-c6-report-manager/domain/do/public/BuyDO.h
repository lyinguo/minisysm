#pragma once 
#include"../DoInclude.h"
class BuyDO :BaseDO
{
	//唯一标识
	MYSQL_SYNTHESIZE(string, id, Id);
	//关联单据
	MYSQL_SYNTHESIZE(string, source,Source);
	//所属组织
	MYSQL_SYNTHESIZE(string, frame, Frame);
	//供应商
	MYSQL_SYNTHESIZE(string, supplier, Supplier);
	//单据时间
	MYSQL_SYNTHESIZE(string, time, Time);
	//单据编号
	MYSQL_SYNTHESIZE(string, number, Number);
	//单据金额
	MYSQL_SYNTHESIZE(double, total, Total);
	//实际金额
	MYSQL_SYNTHESIZE(double, actual, Actual);
	//实付金额
	MYSQL_SYNTHESIZE(double, money, Money);
	//单据费用
	MYSQL_SYNTHESIZE(double, cost, Cost);
	//结算账户
	MYSQL_SYNTHESIZE(string, account, Account);
	//关联人员
	MYSQL_SYNTHESIZE(string, people, People);
	//物流信息
	MYSQL_SYNTHESIZE(string, logistics, Logistics);
	//单据附件
	MYSQL_SYNTHESIZE(string, file, File);
	//备注信息
	MYSQL_SYNTHESIZE(string, data, Data);
	//扩展信息
	MYSQL_SYNTHESIZE(string, more, More);
	//审核状态
	MYSQL_SYNTHESIZE(int, examine,Examine);
	//核销状态
	MYSQL_SYNTHESIZE(int,nucleus, Nucleus);
	//费用状态
	MYSQL_SYNTHESIZE(int, cse, Cse);
	//发票状态
	MYSQL_SYNTHESIZE(int, invoice, Invoice);
	//核对状态
	MYSQL_SYNTHESIZE(int, check, Check);
	//制单人
	MYSQL_SYNTHESIZE(string, user, User);  
public:
	BuyDO() :BaseDO("buy")
	{
		MYSQL_ADD_FIELD_PK("id","s",Id);
		MYSQL_ADD_FIELD("source","s",Source);
		MYSQL_ADD_FIELD("frame","s",Frame);
		MYSQL_ADD_FIELD("supplier","s",Supplier);
		MYSQL_ADD_FIELD("time","dt",Time);
		MYSQL_ADD_FIELD("number","s",Number);
		MYSQL_ADD_FIELD("total","d",Total);
		MYSQL_ADD_FIELD("actual","d",Actual);
		MYSQL_ADD_FIELD("money","d",Money);
		MYSQL_ADD_FIELD("cost","d",Cost);
		MYSQL_ADD_FIELD("account","s",Account);
		MYSQL_ADD_FIELD("people","s",People);
		MYSQL_ADD_FIELD("logistics","s",Logistics);
		MYSQL_ADD_FIELD("file","s",File);
		MYSQL_ADD_FIELD("data","s",Data);
		MYSQL_ADD_FIELD("more","s",More);
		MYSQL_ADD_FIELD("examine","i",Examine);
		MYSQL_ADD_FIELD("nucleus","i",Nucleus);
		MYSQL_ADD_FIELD("cse","i",Cse);
		MYSQL_ADD_FIELD("invoice","i",Invoice);
		MYSQL_ADD_FIELD("check","i",Check);
		MYSQL_ADD_FIELD("user","s",User);
	}
};

typedef std::shared_ptr<BuyDO> PtrBuyDO;