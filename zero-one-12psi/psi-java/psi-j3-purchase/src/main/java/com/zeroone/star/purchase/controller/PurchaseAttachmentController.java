package com.zeroone.star.purchase.controller;

import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.purchase.service.PurchaseAttachmentService;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.*;
import java.util.Map;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

@RestController
@RequestMapping("purchase-note/attachments")
public class PurchaseAttachmentController {
    private final PurchaseAttachmentService service;
    public PurchaseAttachmentController(PurchaseAttachmentService service){this.service=service;}
    @PostMapping("/{purchase}")
    public JsonVO<Map<String,Object>> upload(@PathVariable String purchase,@RequestParam String version,@RequestParam MultipartFile file) throws IOException {
        return JsonVO.success(service.upload(purchase,version,file));
    }
    public static class Removal {public String version;}
    @DeleteMapping("/{purchase}/{id}")
    public JsonVO<Map<String,Object>> remove(@PathVariable String purchase,@PathVariable String id,@RequestBody Removal request){return JsonVO.success(service.remove(purchase,id,request.version));}
    @GetMapping("/{purchase}/{id}")
    public ResponseEntity<byte[]> download(@PathVariable String purchase,@PathVariable String id){
        Map<String,Object> row=service.download(purchase,id);byte[] bytes=(byte[])row.get("body");
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_OCTET_STREAM).contentLength(bytes.length)
            .header(HttpHeaders.CONTENT_DISPOSITION,ContentDisposition.builder("attachment").filename(row.get("name").toString(),StandardCharsets.UTF_8).build().toString())
            .header("X-Content-Type-Options","nosniff").header(HttpHeaders.CACHE_CONTROL,"no-store").body(bytes);
    }
}
