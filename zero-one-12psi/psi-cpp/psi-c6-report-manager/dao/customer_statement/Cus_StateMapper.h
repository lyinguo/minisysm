#pragma once
#include"Mapper.h"
#include "../../domain/do/customer_statement/Cus_StateDO.h"

class Cus_StateOneMapper :public Mapper<Cus_StateOneViewDO>
{
public:
	Cus_StateOneViewDO mapper(ResultSet* resultset) const override
	{
		Cus_StateOneViewDO cs;
		cs.setmold_method(resultset->getString("mold"));
		cs.setframe_method(resultset->getString("frame"));
		cs.settime_method(resultset->getString("time"));
		cs.setnumber_method(resultset->getString("number"));
		cs.setcost_method(resultset->getDouble("cost"));
		cs.setactual_method(resultset->getDouble("actual"));
		cs.setmoney_method(resultset->getDouble("money"));
		cs.setdata_method(resultset->getString("data"));
		return cs;
	}
};

class Cus_StateAllMapper :public Mapper<Cus_StateAllViewDO>
{
public:
	Cus_StateAllViewDO mapper(ResultSet* resultset) const override
	{
		Cus_StateAllViewDO cs;
		cs.setmold_method(resultset->getString("mold"));
		cs.setframe_method(resultset->getString("frame"));
		cs.settime_method(resultset->getString("time"));
		cs.setnumber_method(resultset->getString("number"));
		cs.setcost_method(resultset->getDouble("cost"));
		cs.setactual_method(resultset->getDouble("actual"));
		cs.setmoney_method(resultset->getDouble("money"));
		cs.setdata_method(resultset->getString("data"));
		cs.setgoods_method(resultset->getString("goods"));
		cs.setattr_method(resultset->getString("attr"));
		cs.setunit_method(resultset->getString("unit"));
		cs.setnums_method(resultset->getInt("nums"));
		cs.setdsc_method(resultset->getDouble("dsc"));
		cs.settotal_method(resultset->getDouble("total"));
		cs.settat_method(resultset->getDouble("tat"));
		cs.settpt_method(resultset->getDouble("tpt"));
		return cs;
	}
};