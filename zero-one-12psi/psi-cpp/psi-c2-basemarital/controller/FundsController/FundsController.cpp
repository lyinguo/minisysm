#include "stdafx.h"
#include "FundsController.h"

AccountDetailJsonVO::Wrapper FundsController::excuteQueryDetail(const String& id)
{
	// ���巵�����ݶ���
	auto jvo = AccountDetailJsonVO::createShared();

	// ����У��
	// �ǿ�У��
	if (!id)
	{
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}
	// ����һ��Service
	FundsService service;
	// ִ����������
	auto res = service.getAccountById(id.getValue({}));
	jvo->success(res);

	//��Ӧ���
	return jvo;
}
StringJsonVO::Wrapper FundsController::excuteAdd(const AddAccountDTO::Wrapper& dto, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();
//�ǿ�У��

	if (!dto->accountname|| !dto->accountnumber|| !dto->frame|| !dto->time|| !dto->initial || !dto->balance)
	{
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}
	
//��ЧֵУ��
	if (!dto->accountname->empty() || !dto->accountnumber->empty() || !dto->frame->empty() || !dto->time->empty() || dto->initial < 0 || dto->balance < 0)
	{
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}

	FundsService service;
	dto->setPayload(&payload);
	std::string id = service.saveNewAccount(dto);
	if (id != "") {
		jvo->success(id);
	}
	else
	{
		jvo->fail("");
	}
	//��Ӧ���
	return jvo;
}
StringJsonVO::Wrapper FundsController::excuteModify(const AccountDetailDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// ���巵�����ݶ���
	auto jvo = StringJsonVO::createShared();
	// ����У��
	if (!dto->id)
	{
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}
	// ����һ��Service
	FundsService service;
	// ִ�������޸�
	dto->setPayload(&payload);
	if (service.updateAccount(dto)) {
		jvo->success(dto->id);
	}
	else
	{
		jvo->fail(dto->id);
	}
	// ��Ӧ���
	return jvo;
}

FundsPageJsonVO::Wrapper FundsController::execQueryFunds(const FundsQuery::Wrapper& query)
{
	auto jvo = FundsPageJsonVO::createShared();
	FundsService service;
	auto pageData = service.listFunds(query);
	jvo->success(pageData);
	return jvo;
}

ListJsonVO<String>::Wrapper FundsController::execRemoveFund(const List<String>& ids)
{
	auto json = ListJsonVO<String>::createShared();
	if (!ids)
	{
		json->init(nullptr, RS_PARAMS_INVALID);
		return json;
	}
	FundsService service;
	auto res = service.deleteFunds(ids);
	if (res)
	{
		json->success(ids);
	}
	else
	{
		json->fail(nullptr);
	}
	return json;
}