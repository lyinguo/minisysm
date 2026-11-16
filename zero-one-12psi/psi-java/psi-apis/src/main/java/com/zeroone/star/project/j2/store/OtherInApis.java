package com.zeroone.star.project.j2.store;

import com.zeroone.star.project.dto.j2.store.OtherInListAddDTO;
import com.zeroone.star.project.dto.j2.store.OtherInListDTO;
import com.zeroone.star.project.dto.j2.store.OtherInListDetailDTO;
import com.zeroone.star.project.vo.JsonVO;
import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;
import java.util.List;
import java.util.Map;
import com.zeroone.star.project.dto.j2.store.StockDocumentCommand;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.query.j2.store.OtherInQuery;

/**
 * @BelongsProject: psi-java
 * @BelongsPackage: com.zeroone.star.project.j2.store
 * @Author: 高
 * @CreateTime: 2025-10-19 18:46
 * @Description: 其他入库单接口
 * @Version: 1.0
 */
public interface OtherInApis {
    /**
     * 修改其他入库单
     * @param otherInListDetailDTO 修改参数
     * @return 修改结果
     */
    JsonVO<String> updateOtherInList(OtherInListDetailDTO otherInListDetailDTO);

    /**
     * 审核或反审核
     * @param ids 审核id列表
     * @return 修改结果
     */
    JsonVO<Integer> examine(StockDocumentCommand command);

    /**
     * 核对或反核对
     * @param ids 核对id列表
     * @return 修改结果
     */
    JsonVO<Integer> check(StockDocumentCommand command);

    /**
     * 获取指定其他入库单详细
     * @param id
     * @return
     */
    JsonVO<Map<String,Object>> queryOtherInListDetail(String id);

    /**
     * 新增其他入库单
     * @param dto
     * @return
     */
    JsonVO<String> addOtherInList(OtherInListAddDTO dto);

    /**
     * 删除其他入库单(批量)
     * @param ids
     * @return
     */
    JsonVO<Integer> removeOtherInList(StockDocumentCommand command);

    /**
     *  导入数据
     * @param file 导入的excel文件
     * @return 导入数据的id
     */
    JsonVO<Map<String,Object>> importExcel(MultipartFile file, String version);

    /**
     *  导出简单报表
     * @param ids 需要导出的数据的id,导入格式（暂定）为 "1+2+4+5"（1，2，4，5）为id
     * @return 一张excel表
     */
    ResponseEntity<byte[]> exportEasyExcel(String ids);

    /**
     *  导出详细报表
     * @param ids 需要导出的数据的id,导入格式（暂定）为 "1+2+4+5"（1，2，4，5）为id
     * @return 一张包含所选单据全部商品明细的Excel表
     */
    ResponseEntity<byte[]> exportDetailExcel(String ids);

    /**
     * 获取其他入库单列表
     * @param query 查询参数
     * @return
     */
    JsonVO<Map<String,Object>> listOtherIn(OtherInQuery query);
}
