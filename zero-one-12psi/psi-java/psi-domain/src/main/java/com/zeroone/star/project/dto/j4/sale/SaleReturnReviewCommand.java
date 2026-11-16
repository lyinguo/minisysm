package com.zeroone.star.project.dto.j4.sale;

import lombok.Data;

/** Return IDs and the exact document versions reviewed by the operator. */
@Data
public class SaleReturnReviewCommand extends SaleReviewCommand {
    private Integer status;
}
