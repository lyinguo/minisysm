#include"FundsService.h"
#include"../../dao/FundsDAO/FundsDAO.h"
#include"id/SnowFlake.h"
#include"domain/query/FundsQuery/FundsQuery.h"
#include <string>
/*
* class AddAccountDTO : public oatpp::DTO
{
	DTO_INIT(AddAccountDTO, DTO);
	
	API_DTO_FIELD_DEFAULT(String, accountname, ZH_WORDS_GETTER("funds.field.name"));
	API_DTO_FIELD_DEFAULT(String, accountnumber, ZH_WORDS_GETTER("funds.field.number"));
	API_DTO_FIELD_DEFAULT(String, frame, ZH_WORDS_GETTER("funds.field.frame"));
	API_DTO_FIELD_DEFAULT(String, time, ZH_WORDS_GETTER("funds.field.time"));
	API_DTO_FIELD_DEFAULT(Float64, initial, ZH_WORDS_GETTER("funds.field.initial"));
	API_DTO_FIELD_DEFAULT(Float64, balance, ZH_WORDS_GETTER("funds.field.balance"));
	API_DTO_FIELD_DEFAULT(String, data, ZH_WORDS_GETTER("funds.field.data"));

	// ???????PayloadDTO???????????
	CC_SYNTHESIZE(const PayloadDTO*, _payload, Payload);

};

class AccountDetailDTO :public AddAccountDTO
{
	DTO_INIT(AccountDetailDTO, AddAccountDTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("funds.field.id"));
};
*/
/*
* 	//???id
	MYSQL_SYNTHESIZE(string, id, Id);
	//???????
	MYSQL_SYNTHESIZE(string, accountname, Accountname);
	//??????
	MYSQL_SYNTHESIZE(string, accountnumber, Accountnumber);
	//???????
	MYSQL_SYNTHESIZE(string, frame, Frame);
	//???????
	MYSQL_SYNTHESIZE(string, time, Time);
	//??????
	MYSQL_SYNTHESIZE(double, initial, Initial);
	//??????
	MYSQL_SYNTHESIZE(double, balance, Balance);
	//??????
	MYSQL_SYNTHESIZE(string, data, Data);
*/
//??????
AccountDetailDTO::Wrapper FundsService::getAccountById(std::string id)
{
	AccountDAO dao;
	auto res = dao.selectById(id);
	if (!res) return nullptr;

	auto dto = AccountDetailDTO::createShared();
	ZO_STAR_DOMAIN_DO_TO_DTO_1(dto, res, id, Id, accountname, Accountname, accountnumber, Accountnumber, frame, Frame, time, Time, initial, Initial, balance, Balance, data, Data);
	return dto;
}
//???????
std::string FundsService::saveNewAccount(AddAccountDTO::Wrapper dto)
{
	AccountDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto,
		Accountname, accountname,
		Accountnumber, accountnumber,
		Frame, frame,
		Time, time,
		Initial, initial,
		Balance, balance,
		Data, data
	);
	SnowFlake sf(1, 1);
	data.setId(std::to_string(sf.nextId()));
	AccountDAO dao;
	return dao.insert(data) == 1 ? data.getId() : "";

}
//??????
bool FundsService::updateAccount(AccountDetailDTO::Wrapper dto)
{
	AccountDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto,
		Id, id,
		Accountname, accountname,
		Accountnumber, accountnumber,
		Frame, frame,
		Time, time,
		Initial, initial,
		Balance, balance,
		Data, data
	);

	AccountDAO dao;
	return dao.update(data) == 1;
}
//???
bool FundsService::deleteFunds(const oatpp::List<oatpp::String>& ids)
{
	AccountDAO dao;
	std::list<std::string> datas;
	for (auto one : *ids.get())
	{
		datas.emplace_back(one.getValue({}));
	}
	int rows = dao.deleteByIds<AccountDO>(datas);
	if (rows == ids->size())
	{
		return true;
	}
	return false;
}

FundsPageDTO::Wrapper FundsService::listFunds(const FundsQuery::Wrapper& query)
{
	auto pages = FundsPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	AccountDAO dao;
	uint64_t count = dao.count(query);
	pages->total = count;
	if (count <= 0)
	{
		return pages;
	}

	pages->calcPages();
	auto result = dao.selectWithPage(query);
	for (auto& sub : result)
	{
		auto dto = FundsDTO::createShared();
		dto->name = sub.getAccountname();
		dto->number = sub.getAccountnumber();
		dto->frame = 0;
		dto->time = 0;
		if (!sub.getFrame().empty()) {
			try { dto->frame = std::stoi(sub.getFrame()); } catch (...) {}
		}
		if (!sub.getTime().empty()) {
			try { dto->time = std::stoi(sub.getTime()); } catch (...) {}
		}
		dto->balance = static_cast<float>(sub.getBalance());
		dto->data = sub.getData();
		pages->addData(dto);
	}
	return pages;
}