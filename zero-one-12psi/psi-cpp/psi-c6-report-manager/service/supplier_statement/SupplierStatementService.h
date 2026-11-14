#pragma once

#ifndef _SUPPLIERSTATEMENTSERVICE_
#define _SUPPLIERSTATEMENTSERVICE_

#include "domain/query/supplier_statement/SupplierStatementQuery.h"
#include "domain/dto/supplier_statement/SupplierStatementDTO.h"
#include "domain/vo/supplier_statement/SupplierStatementVO.h"

class SupplierStatementService
{
public:
	SupplierStatementPageDTO::Wrapper listWithPage(const SupplierStatementQuery::Wrapper& query);
};

#endif // _SUPPLIERSTATEMENTSERVICE_