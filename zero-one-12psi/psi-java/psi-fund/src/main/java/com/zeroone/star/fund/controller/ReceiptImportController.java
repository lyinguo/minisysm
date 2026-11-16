package com.zeroone.star.fund.controller;

import com.zeroone.star.fund.service.ReceiptImportService;
import com.zeroone.star.project.vo.JsonVO;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/fund/receipt")
public class ReceiptImportController {
    private final ReceiptImportService imports;
    public ReceiptImportController(ReceiptImportService imports){this.imports=imports;}
    @PostMapping("/import-preview") public JsonVO<Map<String,Object>> preview(@RequestBody ReceiptImportService.Command command){return JsonVO.success(imports.preview(command));}
    @PostMapping("/import-confirm") public JsonVO<Map<String,Object>> save(@RequestBody ReceiptImportService.Command command){return JsonVO.success(imports.save(command));}
    @GetMapping("/import-template") public ResponseEntity<byte[]> template(){
        byte[] bytes=imports.template();
        return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=receipt-template.xlsx")
            .contentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
            .contentLength(bytes.length).body(bytes);
    }
}
