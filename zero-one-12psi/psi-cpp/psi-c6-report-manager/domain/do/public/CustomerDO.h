#pragma once
#ifndef CUSTOMER_DO_H
#define CUSTOMER_DO_H

#include "../DoInclude.h"

class CustomerDO : public BaseDO
{
    MYSQL_SYNTHESIZE(string, id, Id);
    MYSQL_SYNTHESIZE(string, name, Name);
public:
    CustomerDO() : BaseDO("customer")
    {
        MYSQL_ADD_FIELD_PK("id", "s", id);
        MYSQL_ADD_FIELD("name", "s", name);
    }
};
typedef std::shared_ptr<CustomerDO> PtrCustomerDO;
#endif // CUSTOMER_DO_H