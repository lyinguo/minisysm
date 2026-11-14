package com.zeroone.star.basic_information.controller;

import com.zeroone.star.basic_information.service.CustomerImportService;
import com.zeroone.star.project.dto.j6.basic_information.customer_management.CustomerAddDTO;
import com.zeroone.star.project.vo.JsonVO;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/basic_information/customer")
public class CustomerImportController {
    private final CustomerImportService service;
    public CustomerImportController(CustomerImportService service) { this.service = service; }
    @PostMapping("/import")
    public JsonVO<Integer> importCustomers(@RequestBody List<CustomerAddDTO> rows) {
        return JsonVO.success(service.importRows(rows));
    }
}
