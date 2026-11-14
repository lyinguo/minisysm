package com.zeroone.star.basic_information.service.impl;


import com.alibaba.cloud.commons.lang.StringUtils;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.basic_information.entity.Account;
import com.zeroone.star.basic_information.mapper.AccountMapper;
import com.zeroone.star.basic_information.service.IAccountService;
import com.zeroone.star.basic_information.service.util.AccountConverter;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.basic_information.fund_account.AccountDTO;
import com.zeroone.star.project.dto.j6.basic_information.fund_account.AccountListDTO;
import com.zeroone.star.project.dto.j6.basic_information.fund_account.SaveAccountDTO;
import com.zeroone.star.project.query.PageQuery;
import com.zeroone.star.project.query.j6.basic_information.fund_account.AccountQuery;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

/**
 * <p>
 * 描述: 资金账户接口实现类
 * </p>
 *
 * @author goldenHour
 * @version 1.0.0
 */

@Service
public class IAccountServiceImpl extends ServiceImpl<AccountMapper,Account> implements IAccountService {

    @Resource
    AccountMapper accountMapper;

    /**
     * 查询资金账户列表
     * @param accountQuery
     * @param pageQuery
     * @return
     */
    @Override
    public PageDTO<AccountListDTO> listAccounts(AccountQuery accountQuery, PageQuery pageQuery) {
        Page<Account> pageParam  = new Page<>(pageQuery.getPageIndex(), pageQuery.getPageSize());

        LambdaQueryWrapper<Account> queryWrapper = new LambdaQueryWrapper<Account>();
                // 动态添加条件：如果 accountQuery.getName() 不为空，才拼接 like 条件
        queryWrapper.like(StringUtils.isNotBlank(accountQuery.getName()), Account::getName, accountQuery.getName())
                .like(StringUtils.isNotBlank(accountQuery.getNumber()), Account::getNumber, accountQuery.getNumber())
                .like(StringUtils.isNotBlank(accountQuery.getData()), Account::getData, accountQuery.getData());

       Page<Account> pageResult= accountMapper.selectPage(pageParam ,queryWrapper);
        return PageDTO.create(pageResult,AccountListDTO.class);
    }

    /**
     * 获取账户详情
     * @param id
     * @return
     */
    @Override
    public AccountDTO getAccount(String id) {
        Account account = accountMapper.selectById(id);
        return AccountConverter.toDTO(account);
    }

    @Override
    public int addAccount(SaveAccountDTO saveAccountDTO) {
        Account account = AccountConverter.toEntity(saveAccountDTO);
        return accountMapper.insert(account);
    }

    @Override
    public int updateAccount(AccountDTO accountDTO) {
        Account original = accountMapper.selectById(accountDTO.getId());
        if (original == null) throw new IllegalArgumentException("账户不存在，请刷新");
        Account account = AccountConverter.toEntity(accountDTO);
        java.math.BigDecimal previousInitial = original.getInitial() == null ? java.math.BigDecimal.ZERO : original.getInitial();
        java.math.BigDecimal balance = original.getBalance() == null ? java.math.BigDecimal.ZERO : original.getBalance();
        if (accountDTO.getInitial() != null && accountDTO.getInitial().compareTo(previousInitial) != 0) {
            if (balance.compareTo(previousInitial) != 0) throw new IllegalArgumentException("账户余额已发生变化，不能修改期初余额");
            account.setBalance(accountDTO.getInitial());
        } else {
            account.setBalance(balance);
        }
        return accountMapper.updateById(account);
    }

    @Override
    public int deleteAccount(String id) {
        return accountMapper.deleteById(id);
    }

}
