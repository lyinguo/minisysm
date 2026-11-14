#pragma once
#include"../DoInclude.h"

// s1.`type`,s1.`frame`,s1.`customer`,
//      s1.`time`,s1.`number`

class Sale_DetailTypeDO : public BaseDO
{
	//表id
	MYSQL_SYNTHESIZE(string, id, id_method);
	//单据类型
	MYSQL_SYNTHESIZE(string, mold, mold_method);
public:
	Sale_DetailTypeDO() :BaseDO("bill_info")
	{
		MYSQL_ADD_FIELD_PK("id", "s", id);
		MYSQL_ADD_FIELD("mold", "s", mold);
	}
};

typedef std::shared_ptr<Sale_DetailTypeDO> PtrSale_DetailTypeDO;

class Sale_DetailViewDO :public Sale_DetailTypeDO
{
	//所属组织
	MYSQL_SYNTHESIZE(string, frame, frame_method);
	//客户
	MYSQL_SYNTHESIZE(string, customer, customer_method);
	//单据时间
	MYSQL_SYNTHESIZE(string, time, time_method);
	//单据编号
	MYSQL_SYNTHESIZE(string, number, number_method);
	//商品名称
	MYSQL_SYNTHESIZE(string, goods, goods_method);
	//辅助类型
	MYSQL_SYNTHESIZE(string, attr, attr_method);
	//仓库
	MYSQL_SYNTHESIZE(string, warehouse, warehouse_method);
	//单价
	MYSQL_SYNTHESIZE(double, price, price_method);
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
	//备注
	MYSQL_SYNTHESIZE(string, data, data_method);
};
typedef std::shared_ptr<Sale_DetailViewDO> PtrSale_DetailViewDO;