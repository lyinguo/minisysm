#ifndef _WAREHOUSE_H_
#define _WAREHOUSE_H_


#include "oatpp/core/macro/codegen.hpp"
#include "oatpp/core/Types.hpp"
#include "../../GlobalInclude.h"
#include OATPP_CODEGEN_BEGIN(DTO)




/**
 * 仓库信息DTO
 */
class WarehouseInfoDTO : public oatpp::DTO
{
	// 初始化
	DTO_INIT(WarehouseInfoDTO, DTO);

	// 仓库ID
	DTO_FIELD(String, id);
	DTO_FIELD_INFO(id) {
		info->description = ZH_WORDS_GETTER("goods_receipt_dispatch.field.warehouse.id");
	}

	// 仓库名称
	DTO_FIELD(String, name);
	DTO_FIELD_INFO(name) {
		info->description = ZH_WORDS_GETTER("goods_receipt_dispatch.field.warehouse.name");
	}

	// 仓库编号
	DTO_FIELD(String, number);
	DTO_FIELD_INFO(number) {
		info->description = ZH_WORDS_GETTER("goods_receipt_dispatch.field.warehouse.number");
	}

	// 所属组织
	DTO_FIELD(String, frame);
	DTO_FIELD_INFO(frame) {
		info->description = ZH_WORDS_GETTER("goods_receipt_dispatch.field.warehouse.frame");
	}

	// 联系人员
	DTO_FIELD(String, contacts);
	DTO_FIELD_INFO(contacts) {
		info->description = ZH_WORDS_GETTER("goods_receipt_dispatch.field.warehouse.contacts");
	}

	// 联系电话
	DTO_FIELD(String, tel);
	DTO_FIELD_INFO(tel) {
		info->description = ZH_WORDS_GETTER("goods_receipt_dispatch.field.warehouse.tel");
	}

	// 地址
	DTO_FIELD(String, add);
	DTO_FIELD_INFO(add) {
		info->description = ZH_WORDS_GETTER("goods_receipt_dispatch.field.warehouse.add");
	}

	// 扩展数据
	DTO_FIELD(String, data);
	DTO_FIELD_INFO(data) {
		info->description = ZH_WORDS_GETTER("goods_receipt_dispatch.field.warehouse.data");
	}
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_WAREHOUSE_H_



