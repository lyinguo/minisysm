package com.zeroone.star.fund.controller;

import com.zeroone.star.fund.service.*;
import com.zeroone.star.project.vo.JsonVO;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController
@RequestMapping("/fund/receipt")
public class ReceiptSettlementController {
    private final ReceiptSettlementPreviewService preview;
    private final ReceiptSettlementPostingService posting;
    private final ReceiptDraftDocumentService documents;
    public ReceiptSettlementController(ReceiptSettlementPreviewService preview,ReceiptSettlementPostingService posting,ReceiptDraftDocumentService documents){this.preview=preview;this.posting=posting;this.documents=documents;}
    @GetMapping("/settlement-preview") public JsonVO<Map<String,Object>> preview(@RequestParam String id){return JsonVO.success(preview.preview(id));}
    @PostMapping("/settle") public JsonVO<Integer> settle(@RequestBody ReceiptSettlementPostingService.Command command){return JsonVO.success(posting.post(command));}
    @GetMapping("/document/{id}") public JsonVO<Map<String,Object>> document(@PathVariable String id){return JsonVO.success(documents.document(id));}
    @GetMapping("/documents") public JsonVO<Map<String,Object>> list(@RequestParam Map<String,String> query){return JsonVO.success(documents.list(query));}
    @PutMapping("/document/{id}") public JsonVO<String> revise(@PathVariable String id,@RequestBody ReceiptDraftDocumentService.Revision command){return JsonVO.success(documents.revise(id,command));}
    @DeleteMapping("/document/{id}") public JsonVO<String> remove(@PathVariable String id,@RequestBody ReceiptDraftDocumentService.Removal command){if(command==null)throw new IllegalArgumentException("请提交收款草稿已读版本");return JsonVO.success(documents.delete(id,command.version));}
    @GetMapping("/options") public JsonVO<Map<String,Object>> options(@RequestParam String kind,@RequestParam(defaultValue="") String keyword,@RequestParam(required=false) String document){return JsonVO.success(documents.options(kind,keyword,document));}
}
