
/*
 Copyright Zero One Star. All rights reserved.

 @Author: awei
 @Date: 2025/10/13 21:38:24

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

	  https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/
#include "stdafx.h"
#include "service/user/UserService.h"
#include "UserController.h"
#include "../../security/SystemIdentityAccess.h"
#include<string>

static size_t utf8Chars(const oatpp::String& value)
{
    if (!value) return 0;
    size_t count = 0;
    for (unsigned char character : *value) if ((character & 0xc0) != 0x80) ++count;
    return count;
}


//负责设置VO的失败状态
#define SET_VO_FAIL(vo, err_code, err_msg) \
    do { \
        (vo)->code = (err_code); \
        (vo)->message = ZH_WORDS_GETTER(err_msg); \
        (vo)->data = ""; \
    } while(0)
//初始化成功响应
#define INIT_VO_SUCCESS(vo) \
    do { \
        (vo)->code = 10000; \
        (vo)->message = ZH_WORDS_GETTER("user.success"); \
        (vo)->data = ""; \
    } while(0)
//检查手机号码格式--长度是否为11？第一位是否是1？是否全是数字？
#define CHECK_TEL_FORM(s_tel) \
    do { \
        std::string tel((s_tel)->c_str(), (s_tel)->size()); \
		if(tel.size()!=11){\
			SET_VO_FAIL(uvo, 9999, "user.tel.length_error"); \
            return uvo; \
		}\
        if (tel[0] != '1') { \
            SET_VO_FAIL(uvo, 9999, "user.tel.form_error"); \
            return uvo; \
        }\
        for (int i = 1; i < tel.size(); i++) { \
            if (tel[i] < '0' || tel[i] > '9') { \
                SET_VO_FAIL(uvo, 9999, "user.tel.form_error"); \
                return uvo; \
            } \
        } \
    } while(0)
//检查id是否为空？是否为32位？是否存在该id用户？
#define CHECK_ID_FORM(id) \
do{\
	if (id == nullptr || id->empty()) {\
		SET_VO_FAIL(uvo, 9999, "user.id.empty_error");\
		return uvo;\
	}\
	if (utf8Chars(id) > 32) {\
		SET_VO_FAIL(uvo, 9999, "user.id.length_error");\
		return uvo;\
	}\
	if (!us.checkIdExists(id)) {\
		SET_VO_FAIL(uvo, 9999, "user.id.exist_error");\
		return uvo;\
	}\
}while(0)
//检查是否非空
#define CHECK_FIELD_NOT_EMPTY(field, err_msg) \
    do { \
        if ((dto)->field == nullptr || (dto)->field->empty()) { \
            SET_VO_FAIL(uvo, 9999, err_msg); \
            return uvo; \
        } \
    } while(0)
//检查长度是否超限
#define CHECK_FIELD_MAX_LENGTH(field, max_len, err_msg) \
    do { \
        if ((dto)->field != nullptr && utf8Chars((dto)->field) > (max_len)) { \
            SET_VO_FAIL(uvo, 9999, err_msg); \
            return uvo; \
        } \
    } while(0)
//检查该字段值是否已在数据库中存在
#define CHECK_VALUE_EXISTS(check_func, field, err_msg) \
    do { \
        if (check_func((dto)->field)) { \
            SET_VO_FAIL(uvo, 9999, err_msg); \
            return uvo; \
        } \
    } while(0)
//检查该字段值是否不在数据库中
#define CHECK_VALUE_NOT_EXISTS(check_func, field, err_msg) \
    do { \
        if (!check_func((dto)->field)) { \
            SET_VO_FAIL(uvo, 9999, err_msg); \
            return uvo; \
        } \
    } while(0)
UserJsonVO::Wrapper UserController::executeAddUser(const UserAddDTO::Wrapper& dto, const PayloadDTO& payload)
{
	//service实例
	UserService us;
	//创建响应并初始化
	auto uvo = UserJsonVO::createShared();
    if (!canManageSystemIdentity(payload)) {
        uvo->code=403;uvo->message=u8"只有当前系统管理员可以维护用户账号";return uvo;
    }
	INIT_VO_SUCCESS(uvo);
    if (!dto || !dto->pwd || dto->pwd->empty()) {
        uvo->code = 9999;
        uvo->message = "Password is required";
        return uvo;
    }

	//依次检查字段合法性
//---------------------------------------------------------------------------------------//	
	//检查用户名存在性和长度合法性
	{
		CHECK_FIELD_NOT_EMPTY(name, "user.name.empty_error");
		CHECK_FIELD_MAX_LENGTH(name, 32, "user.name.length_error");
	}
	//检查账号存在性、唯一性和长度合法性
	{
		CHECK_FIELD_NOT_EMPTY(user, "user.user.empty_error");
		CHECK_FIELD_MAX_LENGTH(user, 32, "user.user.length_error");
		CHECK_VALUE_EXISTS(us.checkUserExists, user, "user.user.exist_error");
	}
	//检查手机号码存在性、唯一性和长度合法性
	{
		CHECK_FIELD_NOT_EMPTY(tel, "user.tel.empty_error");
		CHECK_TEL_FORM(dto->tel);
		CHECK_VALUE_EXISTS(us.checkTelExists, tel, "user.tel.exist_error");
	}
	//检查组织存在性和长度合法性
	{
		CHECK_FIELD_NOT_EMPTY(frame, "user.frame.empty_error");
		CHECK_FIELD_MAX_LENGTH(frame, 32, "user.frame.length_error");
		CHECK_VALUE_NOT_EXISTS(us.checkFrameExists, frame, "user.frame.exist_error");

	}
	//检查角色存在性和长度合法性
	{
		CHECK_FIELD_NOT_EMPTY(role,"user.role.empty_error");
		CHECK_FIELD_MAX_LENGTH(role, 32, "user.role.length_error");
		CHECK_VALUE_NOT_EXISTS(us.checkRoleExists, role, "user.role.exist_error");
	}
	//检验非必填字段是否合法
//---------------------------------------------------------------------------------------//	
	//检查密码长度合法性
	{
		if (dto->pwd != nullptr && !dto->pwd->empty()) {
			//若非空，调用宏检查长度
			CHECK_FIELD_MAX_LENGTH(pwd, 20, "user.pwd.length_error");
		}
	}
	//检查备注长度合法性
	{
		if (dto->data != nullptr && !dto->data->empty()) {
			//若非空，调用宏检查长度
			CHECK_FIELD_MAX_LENGTH(data, 256, "user.data.length_error");
		}
	}
	////检查拼音长度合法性
	//{
	//	if (dto->py != nullptr && !dto->py->empty()) {
	//		//若非空，调用宏检查长度
	//		CHECK_FIELD_MAX_LENGTH(data, 256, "user.py.length_error");
	//	}
	//}
	//用户头像检查？
	//调用service层添加用户
	String id=us.addUser(dto);
	if (id == nullptr || id->empty()) {
		SET_VO_FAIL(uvo, 9999, "user.fail");
		return uvo;
	}
	//二度确认成功响应
	INIT_VO_SUCCESS(uvo);
	uvo->data = id;
	return uvo;
}

UserJsonVO::Wrapper UserController::executeModUser(const UserModDTO::Wrapper& dto, const PayloadDTO& payload)
{
    UserService us;
    auto uvo = UserJsonVO::createShared();
    if (!canManageSystemIdentity(payload)) {
        uvo->code=403;uvo->message=u8"只有当前系统管理员可以维护用户账号";return uvo;
    }
    INIT_VO_SUCCESS(uvo);
    if (!dto) { SET_VO_FAIL(uvo, 9999, "user.id.empty_error"); return uvo; }
    CHECK_ID_FORM(dto->id);
    UserDAO dao;
    auto original = dao.selectById(dto->id.getValue(""));
    if (!original) { SET_VO_FAIL(uvo, 9999, "user.id.exist_error"); return uvo; }
    if (dto->name) {
        CHECK_FIELD_NOT_EMPTY(name, "user.name.empty_error");
        CHECK_FIELD_MAX_LENGTH(name, 32, "user.name.length_error");
    }
    if (dto->user) {
        CHECK_FIELD_NOT_EMPTY(user, "user.user.empty_error");
        CHECK_FIELD_MAX_LENGTH(user, 32, "user.user.length_error");
        if (dto->user.getValue("") != original->getUser()) {
            uvo->code = 9999;
            uvo->message = u8"登录账号创建后不能修改，请保留历史关联";
            return uvo;
        }
    }
    if (dto->tel) {
        CHECK_FIELD_NOT_EMPTY(tel, "user.tel.empty_error");
        CHECK_TEL_FORM(dto->tel);
        if (dto->tel.getValue("") != original->getTel() && us.checkTelExists(dto->tel, dto->id)) {
            SET_VO_FAIL(uvo, 9999, "user.tel.exist_error"); return uvo;
        }
    }
    if (dto->frame) {
        CHECK_FIELD_NOT_EMPTY(frame, "user.frame.empty_error");
        CHECK_FIELD_MAX_LENGTH(frame, 32, "user.frame.length_error");
        CHECK_VALUE_NOT_EXISTS(us.checkFrameExists, frame, "user.frame.exist_error");
    }
    if (dto->role) {
        CHECK_FIELD_NOT_EMPTY(role, "user.role.empty_error");
        CHECK_FIELD_MAX_LENGTH(role, 32, "user.role.length_error");
        CHECK_VALUE_NOT_EXISTS(us.checkRoleExists, role, "user.role.exist_error");
    }
    if (dto->pwd && !dto->pwd->empty()) CHECK_FIELD_MAX_LENGTH(pwd, 20, "user.pwd.length_error");
    if (dto->data) CHECK_FIELD_MAX_LENGTH(data, 256, "user.data.length_error");
    if (dto->py) CHECK_FIELD_MAX_LENGTH(py, 32, "user.name.length_error");
    if (us.modUser(dto)) { INIT_VO_SUCCESS(uvo); uvo->data = dto->id; }
    else { SET_VO_FAIL(uvo, 9999, "user.fail"); }
    return uvo;
}

UserJsonVO::Wrapper UserController::executeDelUser(const String& id, const PayloadDTO& payload)
{
	//service实例
	UserService us;
	//创建响应
	auto uvo = UserJsonVO::createShared();
    if (!canManageSystemIdentity(payload)) {
        uvo->code=403;uvo->message=u8"只有当前系统管理员可以维护用户账号";return uvo;
    }
	INIT_VO_SUCCESS(uvo);
	//检查id存在性和长度合法性
	{
		CHECK_ID_FORM(id);
	}
	//调用service层删除用户
	if (us.delUser(id)) {
		INIT_VO_SUCCESS(uvo);
		uvo->data = id;
	}
	else {
		SET_VO_FAIL(uvo, 9999, "user.fail");
	}
	return uvo;
}

UserPageJsonVO::Wrapper UserController::executeQueryAll(const UserQuery::Wrapper& query)
{
	UserService us;
	auto vo = UserPageJsonVO::createShared();

	// 输入检查逻辑
	// 1. 检查用户名称长度
	if (query->name != nullptr && !query->name->empty()) {
		if (utf8Chars(query->name) > 32) {
			vo->code = 9999;
			vo->message = u8"用户名称过长（最大32个字符）";
			vo->data = {};
			return vo;
		}
	}

	// 2. 检查用户账号长度
	if (query->user != nullptr && !query->user->empty()) {
		if (utf8Chars(query->user) > 32) {
			vo->code = 9999;
			vo->message = u8"用户账号过长（最大32个字符）";
			vo->data = {};
			return vo;
		}
	}

	// 3. 检查手机号码格式（非空时）
	if (query->tel != nullptr && !query->tel->empty()) {
		std::string tel(query->tel->c_str(), query->tel->size());
		// 检查长度是否为11位
		if (tel.size() > 11) {
			vo->code = 9999;
			vo->message = u8"手机号码格式错误（必须小于11位）";
			vo->data = {};
			return vo;
		}
		// 检查首位是否为1
		if (tel[0] != '1') {
			vo->code = 9999;
			vo->message = u8"手机号码格式错误（必须是1开头）";
			vo->data = {};
			return vo;
		}
		// 检查其余位是否为数字
		for (int i = 1; i < tel.size(); i++) {
			if (tel[i] < '0' || tel[i] > '9') {
				vo->code = 9999;
				vo->message = u8"手机号码格式错误（只能包含数字）";
				vo->data = {};
				return vo;
			}
		}
	}

	// 4. 检查备注信息长度
	if (query->data != nullptr && !query->data->empty()) {
		if (utf8Chars(query->data) > 256) {
			vo->code = 9999;
			vo->message = u8"备注信息过长（最大256个字符）";
			vo->data = {};
			return vo;
		}
	}

	// 检查通过，执行查询
	auto result = us.listAll(query);
	// 关键修改：判断分页结果中是否无数据（total=0或rows为空）
	if (result == nullptr) {
		vo->code = 9999;
		vo->message = u8"无符合要求的用户存在";
		vo->data = {};
	}
	else {
		vo->success(result);
	}
	return vo;
}

UserDetailJsonVO::Wrapper UserController::executeQueryOne(const String& id)
{
	UserService us;
	auto jvo = UserDetailJsonVO::createShared();

	// 输入检查逻辑
	// 1. 检查ID是否为空
	if (id == nullptr || id->empty()) {
		jvo->code = 9999;
		jvo->message = u8"ID必须输入";
		jvo->data = {};
		return jvo;
	}

	// 检查通过，执行查询
	auto data = us.getUserDetail(id);
	if (data) {
		jvo->success(data);
	}
	else {
		// 数据为null时返回u8"该用户不存在"
		jvo->code = 9999;
		jvo->message = u8"该用户不存在";
		jvo->data = {};
	}
	return jvo;
}
