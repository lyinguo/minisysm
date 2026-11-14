#pragma once

#ifndef _SUPPLIERSTATEMENTVO_
#define _SUPPLIERSTATEMENTVO_

#include "../../GlobalInclude.h"
#include "../../dto/supplier_statement/SupplierStatementDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

class SupplierStatementDetailJsonVO : public JsonVO<SupplierStatementDetailDTO::Wrapper> {
	DTO_INIT(SupplierStatementDetailJsonVO, JsonVO<SupplierStatementDetailDTO::Wrapper>);
};

class SupplierStatementItemJsonVO : public JsonVO<SupplierStatementItemDTO::Wrapper> {
	DTO_INIT(SupplierStatementItemJsonVO, JsonVO<SupplierStatementItemDTO::Wrapper>);
};

class SupplierStatementJsonVO : public JsonVO<SupplierStatementDTO::Wrapper> {
	DTO_INIT(SupplierStatementJsonVO, JsonVO<SupplierStatementDTO::Wrapper>);
};

class SupplierStatementPageJsonVO : public JsonVO<SupplierStatementPageDTO::Wrapper> {
	DTO_INIT(SupplierStatementPageJsonVO, JsonVO<SupplierStatementPageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_SUPPLIERSTATEMENTVO_