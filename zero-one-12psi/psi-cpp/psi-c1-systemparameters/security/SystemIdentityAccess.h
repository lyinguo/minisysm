#pragma once
#include "SqlSession.h"
#include "domain/dto/PayloadDTO.h"

// Account and role maintenance must use the current persistent administrator
// identity, not the authority claim of a token issued before demotion.
inline bool canManageSystemIdentity(const PayloadDTO& payload)
{
    if (payload.getId().empty()) return false;
    try {
        SqlSession session;
        SqlParams params;
        SQLPARAMS_PUSH(params, "s", std::string, payload.getId());
        return session.executeQueryNumerical(
            "SELECT COUNT(*) FROM `user` WHERE id=? AND role='0'", params) == 1;
    } catch (const std::exception&) {
        return false;
    }
}
