package com.zeroone.star.project.dto.j4.sale;
import lombok.Data;
import java.util.List;
import java.util.Map;
/** The exact versions displayed to the operator; never obtain them inside a command. */
@Data
public class SaleReviewCommand {
    private List<String> ids;
    private String version;
    private Map<String,String> versions;
}
