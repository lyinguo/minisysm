package com.zeroone.star.basic_information.service;

import com.zeroone.star.basic_information.entity.Account;
import com.zeroone.star.basic_information.mapper.AccountMapper;
import com.zeroone.star.basic_information.service.impl.IAccountServiceImpl;
import com.zeroone.star.project.dto.j6.basic_information.fund_account.AccountDTO;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.mockito.ArgumentCaptor;
import java.math.BigDecimal;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AccountBalanceTest {
    @Test void updatingNameDoesNotResetCurrentBalanceToOpeningBalance() {
        AccountMapper mapper=mock(AccountMapper.class);
        IAccountServiceImpl service=new IAccountServiceImpl();
        ReflectionTestUtils.setField(service,"accountMapper",mapper);
        when(mapper.selectById("a")).thenReturn(Account.builder().id("a").initial(new BigDecimal("10")).balance(new BigDecimal("25")).build());
        service.updateAccount(AccountDTO.builder().id("a").name("新名称").initial(new BigDecimal("10")).build());
        ArgumentCaptor<Account> captor=ArgumentCaptor.forClass(Account.class); verify(mapper).updateById(captor.capture());
        assertEquals(0,new BigDecimal("25").compareTo(captor.getValue().getBalance()));
    }
    @Test void cannotReplaceOpeningBalanceAfterBalanceChanged() {
        AccountMapper mapper=mock(AccountMapper.class); IAccountServiceImpl service=new IAccountServiceImpl();
        ReflectionTestUtils.setField(service,"accountMapper",mapper);
        when(mapper.selectById("a")).thenReturn(Account.builder().id("a").initial(BigDecimal.TEN).balance(new BigDecimal("25")).build());
        assertThrows(IllegalArgumentException.class,()->service.updateAccount(AccountDTO.builder().id("a").initial(new BigDecimal("99")).build()));
        verify(mapper,never()).updateById(any());
    }
}
