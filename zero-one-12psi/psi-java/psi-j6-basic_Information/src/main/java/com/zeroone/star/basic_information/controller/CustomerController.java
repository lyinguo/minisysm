package com.zeroone.star.basic_information.controller;

import com.zeroone.star.basic_information.entity.Customer;
import com.zeroone.star.basic_information.service.ISCustomerService;
import com.zeroone.star.basic_information.service.impl.CustomerServiceImpl;
import com.zeroone.star.basic_information.service.impl.MsCustomerMapper;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.basic_information.customer_management.CustomerAddDTO;
import com.zeroone.star.project.dto.j6.basic_information.customer_management.CustomerDTO;
import com.zeroone.star.project.j6.basic_information.customer_management.CustomerAPis;
import com.zeroone.star.project.query.j6.basic_information.customer_management.CustomerQuery;
import com.zeroone.star.project.vo.JsonVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiImplicitParam;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import io.swagger.models.auth.In;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.util.List;

/**
 * 客户， 控制器
 * @author cmanPro
 */
@RestController
@RequestMapping("/basic_information/customer")
@Api(tags = "客户管理")
@Validated
public class CustomerController implements CustomerAPis {
    @Resource
    ISCustomerService customerService;

    @Resource
    MsCustomerMapper msCustomerMapper;
    @Autowired
    private CustomerServiceImpl customerServiceImpl;

    @GetMapping("/query-all")
    @ApiOperation(value = "查询所有数据")
    public JsonVO<PageDTO<CustomerDTO>> queryAll(@Validated CustomerQuery condition) {
        return JsonVO.success(customerService.listAll(condition));
    }

    @Override
    @GetMapping("/query-one")
    @ApiOperation("查询客户信息")
    @ApiImplicitParam(name = "id", value = "客户ID", required = true)
    public JsonVO<CustomerDTO> queryCustomerById(String id)
    {
        return JsonVO.success(customerService.getById(id));
    }

    @PostMapping("/add-customer")
    @ApiOperation("添加客户")
    @Override
    public JsonVO<String> addCustomer(@Validated @RequestBody CustomerAddDTO customerAddDTO) {
        try {
            Customer customer = msCustomerMapper.addDtoToCustomer(customerAddDTO);
            if (customer.getId() == null || customer.getId().isEmpty()) {
                // id 列 varchar(32)，使用时间戳避免超长
                customer.setId(String.valueOf(System.currentTimeMillis()));
            }
            if (customer.getPy() == null || customer.getPy().isEmpty()) {
                customer.setPy(customer.getNumber() != null ? customer.getNumber() : customer.getName());
            }
            if (customer.getFrame() == null || customer.getFrame().isEmpty()) {
                customer.setFrame("0");
            }
            if (customer.getUser() == null || customer.getUser().isEmpty()) {
                customer.setUser("admin");
            }
            if (customer.getCategory() == null || customer.getCategory().isEmpty()) {
                customer.setCategory("常规类别");
            }
            if (customer.getGrade() == null || customer.getGrade().isEmpty()) {
                customer.setGrade("常规等级");
            }
            if (customer.getMore() == null || customer.getMore().isEmpty()) {
                customer.setMore("{}");
            }
            if (customer.getContacts() == null || customer.getContacts().isEmpty()) {
                customer.setContacts("[]");
            }
            if (customer.getBalance() == null) {
                customer.setBalance(0.0);
            }
            if (customerService.save(customer)) {
                return JsonVO.success(customer.getId());
            }
            return JsonVO.fail("保存客户失败");
        } catch (Exception e) {
            e.printStackTrace();
            return JsonVO.fail(e.getMessage() != null ? e.getMessage() : "添加客户失败");
        }
    }

    @PutMapping("/update-customer")
    @ApiOperation("修改客户信息")
    @Override
    public JsonVO<String> updateCustomer(@Validated @RequestBody CustomerDTO customerDTO) {
        if(customerService.updateById(msCustomerMapper.customerDtoToCustomer(customerDTO))){
            return JsonVO.success(customerDTO.getId());
        }
        return JsonVO.fail(null);
    }

    @DeleteMapping("/delete-customer-list")
    @ApiOperation("删除客户")
    @Override
    public JsonVO<List<String>> deleteCustomer( @ApiParam(value = "客户ID列表", required = true, example = "[\"1\", \"2\"]") @RequestBody List<String> ids) {
        if(customerService.removeByIds(ids)){
            return JsonVO.success(ids);
        }
        return JsonVO.fail(null);
    }
}
