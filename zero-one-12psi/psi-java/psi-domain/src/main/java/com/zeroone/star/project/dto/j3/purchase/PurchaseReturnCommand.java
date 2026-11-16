package com.zeroone.star.project.dto.j3.purchase;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class PurchaseReturnCommand {
    private List<String> ids;
    private String version;
    private Map<String,String> versions;
    private Integer status;
}
