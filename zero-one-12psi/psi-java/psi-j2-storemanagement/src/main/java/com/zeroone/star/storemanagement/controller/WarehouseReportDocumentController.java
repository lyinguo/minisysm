package com.zeroone.star.storemanagement.controller;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.service.WarehouseReportDocumentService;
import com.zeroone.star.storemanagement.service.StockDocumentAccess;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import java.util.*;

@RestController
@RequestMapping("/transfer/report-documents")
public class WarehouseReportDocumentController {
    private final WarehouseReportDocumentService service;
    private final StockDocumentAccess access;
    public WarehouseReportDocumentController(WarehouseReportDocumentService service, StockDocumentAccess access) {
        this.service = service; this.access = access;
    }
    private UserDTO authorize(String kind, String action) {
        return access.authorize(kind, action);
    }
    private String frame(UserDTO user) {
        return access.frame(user);
    }
    private void checkFrame(String kind, String id, UserDTO user) {
        String allowed = frame(user);
        if (allowed != null) {
            Map<?, ?> head = (Map<?, ?>) service.detail(kind, id).get("header");
            if (!allowed.equals(String.valueOf(head.get("frame")))) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "不能操作其他组织的单据");
        }
    }
    @GetMapping("/{kind}")
    public JsonVO<Map<String, Object>> list(@PathVariable String kind, @RequestParam(defaultValue="1") int pageIndex, @RequestParam(defaultValue="20") int pageSize, @RequestParam(defaultValue="") String number) throws Exception {
        UserDTO user = authorize(kind, "read");
        return JsonVO.success(service.list(kind, pageIndex, pageSize, number, frame(user)));
    }
    @GetMapping("/{kind}/{id}")
    public JsonVO<Map<String, Object>> detail(@PathVariable String kind, @PathVariable String id) throws Exception { UserDTO user = authorize(kind, "detail"); checkFrame(kind, id, user); return JsonVO.success(service.detail(kind, id)); }
    @PutMapping("/{kind}/{id}")
    public JsonVO<Map<String, Object>> save(@PathVariable String kind, @PathVariable String id, @RequestBody WarehouseReportDocumentService.Edit edit) throws Exception {
        UserDTO user = authorize(kind, "save"); checkFrame(kind, id, user);
        return JsonVO.success(service.save(kind, id, edit, user.getId()));
    }
    @PostMapping("/{kind}/{id}/audit")
    public JsonVO<Map<String, Object>> audit(@PathVariable String kind, @PathVariable String id, @RequestBody Map<String, Object> body) throws Exception {
        UserDTO user = authorize(kind, "audit"); checkFrame(kind, id, user);
        return JsonVO.success(service.audit(kind, id, Integer.parseInt(String.valueOf(body.get("target"))), String.valueOf(body.get("version")), user.getId()));
    }
}
