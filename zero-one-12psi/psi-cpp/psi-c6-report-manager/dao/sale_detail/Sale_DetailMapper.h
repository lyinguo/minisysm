#pragma once 
#include"Mapper.h"
#include"../../domain/do/sale_detail/Sale_DetailDO.h"
class Sale_DetailMapper :public Mapper<Sale_DetailViewDO>
{
public:
	Sale_DetailViewDO mapper(ResultSet* resultset) const override
	{
		Sale_DetailViewDO sdvdo;
		sdvdo.setmold_method(resultset->getString("mold"));
		sdvdo.setframe_method(resultset->getString("frame"));
		sdvdo.setcustomer_method(resultset->getString("customer"));
		sdvdo.settime_method(resultset->getString("time"));
		sdvdo.setnumber_method(resultset->getString("number"));
		sdvdo.setgoods_method(resultset->getString("goods"));
		sdvdo.setattr_method(resultset->getString("attr"));
		sdvdo.setwarehouse_method(resultset->getString("warehouse"));
		sdvdo.setunit_method(resultset->getString("unit"));
		sdvdo.setprice_method(resultset->getDouble("price"));
		sdvdo.setnums_method(resultset->getInt("nums"));
		sdvdo.setdsc_method(resultset->getDouble("dsc"));
		sdvdo.settotal_method(resultset->getDouble("total"));
		sdvdo.settat_method(resultset->getDouble("tat"));
		sdvdo.settpt_method(resultset->getDouble("tpt"));
		sdvdo.setdata_method(resultset->getString("data"));
		return sdvdo;
	}
};