package com.zeroone.star.project.dto.j3.purchase;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/** Source IDs and quantities are inputs; source-controlled goods/prices/amounts are not trusted inputs. */
@Data
public class PurchaseReturnDraftDTO {
    private String id;
    private String source;
    private String sourceVersion;
    private String version;
    private String frame;
    private String supplier;
    private String user;
    @JsonFormat(pattern="yyyy-MM-dd HH:mm:ss")
    private LocalDateTime time;
    private String number;
    private BigDecimal money;
    private BigDecimal cost;
    private BigDecimal total;
    private BigDecimal actual;
    private String account;
    private String people;
    private String logistics;
    private String file;
    private String data;
    private String more;
    private Integer examine;
    private Integer check;
    private Integer nucleus;
    private Integer cse;
    private Integer invoice;
    private Line[] details;
    @Data public static class Line {
        private String id;
        private String pid;
        private String source;
        private BigDecimal nums;
        private String serial;
        private String data;
    }
}
