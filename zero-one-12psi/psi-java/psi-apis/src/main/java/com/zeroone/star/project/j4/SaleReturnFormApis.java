package com.zeroone.star.project.j4;

import com.zeroone.star.project.vo.JsonVO;
import io.swagger.annotations.ApiParam;

import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j4.sale.SaleReturnDTO;
import com.zeroone.star.project.dto.j4.sale.SaleReturnInfoDTO;
import com.zeroone.star.project.query.j4.sale.SaleReturnQuery;

import java.util.List;

import com.zeroone.star.project.dto.j4.sale.SalesReturnOrderDTO;

import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;

import com.zeroone.star.project.dto.j4.sale.SaleReturnIdsDTO;

/**
 * <p>
 * 描述：销售管理-销售退货单接口
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
public interface SaleReturnFormApis {
    /**
     * 新增销售退货单
     */
    JsonVO<String> addSalesReturnOrder(SalesReturnOrderDTO dto);

    /**
     * 修改销售退货单
     */
    JsonVO<String> updateSalesReturnOrder(SalesReturnOrderDTO dto);

    /**
     * 删除销售退货单
     */
    JsonVO<String> deleteSalesReturnOrder(String id, String version);

    /**
     * 查询退货订单
     * @param saleReturnQuery
     * @return
     */
    JsonVO<PageDTO<java.util.Map<String,Object>>> querySaleReturnList(SaleReturnQuery saleReturnQuery);

    /**
     * 查询退货订单详情
     * @param id
     * @return
     */
    JsonVO<List<java.util.Map<String,Object>>> querySaleReturnInfoList(String id);

    public JsonVO<String> exportSimpleFund();

    public ResponseEntity<String> importFund(@ApiParam("导入退货单文件") MultipartFile file) ;

    public JsonVO<String> exportDetailFund();
    /**
     * 核对/反核对销售退货单
     */
    JsonVO salereturncheck(com.zeroone.star.project.dto.j4.sale.SaleReturnReviewCommand command);
    /**
     * 审核/反审核销售退货单
     */
    JsonVO examine(SaleReturnIdsDTO saleReturnIdsDTO);
}
