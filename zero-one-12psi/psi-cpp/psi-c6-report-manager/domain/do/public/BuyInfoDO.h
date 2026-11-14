#pragma once 
#include"../DoInclude.h"
class BuyInfoDO :BaseDO
{
	//唯一标识
	MYSQL_SYNTHESIZE(string, id, Id);
	//所属id
	MYSQL_SYNTHESIZE(string, pid, Pid);
	//关联详情
	MYSQL_SYNTHESIZE(string, source, Source);
	//所属商品
	MYSQL_SYNTHESIZE(string, goods, Goods);
	//辅助属性
	MYSQL_SYNTHESIZE(string, attr, Attr);
	//单位
	MYSQL_SYNTHESIZE(string, unit, Unit);
	//仓库
	MYSQL_SYNTHESIZE(string, warehouse,Warehouse);
	//批次号
	MYSQL_SYNTHESIZE(string, batch, Batch);
	//生产日期
	MYSQL_SYNTHESIZE(string, mfd, Mfd);
	//单价
	MYSQL_SYNTHESIZE(double, price, Price);
	//数量
	MYSQL_SYNTHESIZE(double, nums, Nums);
	//序列号
	MYSQL_SYNTHESIZE(string, serial, Serial);
	//折扣率
	MYSQL_SYNTHESIZE(double, discount, Discount);
	//折扣额
	MYSQL_SYNTHESIZE(double, dsct, Dsc);
	//金额
	MYSQL_SYNTHESIZE(double, total, Total);
	//税率
	MYSQL_SYNTHESIZE(double, tax, Tax);
	//税额
	MYSQL_SYNTHESIZE(double, tat, Tat);
	//价税合计
	MYSQL_SYNTHESIZE(double, tpt, Tpt);
	//备注信息
	MYSQL_SYNTHESIZE(string, data, Data);
	//退货数量
	MYSQL_SYNTHESIZE(double, retreat, Retreat);
public:
	BuyInfoDO() :BaseDO("buy_info")
	{
		MYSQL_ADD_FIELD_PK("id","s",Id);
		MYSQL_ADD_FIELD("pid","s",Pid);
		MYSQL_ADD_FIELD("source","s",Source);
		MYSQL_ADD_FIELD("goods","s",Goods);
		MYSQL_ADD_FIELD("attr","s",Attr);
		MYSQL_ADD_FIELD("unit","s",Unit);
		MYSQL_ADD_FIELD("warehouse","s",Warehouse);
		MYSQL_ADD_FIELD("batch","s",Batch);
		MYSQL_ADD_FIELD("mfd","dt",Mfd);
		MYSQL_ADD_FIELD("price","d",Price);
		MYSQL_ADD_FIELD("nums","d",Nums);
		MYSQL_ADD_FIELD("serial","s",Serial);
		MYSQL_ADD_FIELD("discount","d",Discount);
		MYSQL_ADD_FIELD("dsc","d",Dsc);
		MYSQL_ADD_FIELD("total","d",Total);
		MYSQL_ADD_FIELD("tax","d",Tax);
		MYSQL_ADD_FIELD("tat","d",Tat);
		MYSQL_ADD_FIELD("tpt","d",Tpt);
		MYSQL_ADD_FIELD("data","s",Data);
		MYSQL_ADD_FIELD("retreat","d",Retreat);
	}
};

typedef std::shared_ptr<BuyInfoDO> PtrBuyInfoDO;