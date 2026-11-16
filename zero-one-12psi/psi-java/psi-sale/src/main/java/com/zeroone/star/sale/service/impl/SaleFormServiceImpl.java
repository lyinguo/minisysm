package com.zeroone.star.sale.service.impl;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j4.sale.SaleDTO;
import com.zeroone.star.project.dto.j4.sale.SaleDetailDTO;
import com.zeroone.star.project.dto.j4.sale.SaleListDTO;
import com.zeroone.star.project.dto.j4.sale.SaleReturnGenerateDTO;
import com.zeroone.star.project.query.j4.sale.SaleQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.project.vo.ResultStatus;
import com.zeroone.star.sale.entity.SaleDO;
import com.zeroone.star.sale.entity.SaleForm;
import com.zeroone.star.sale.entity.SaleInfoDO;
import com.zeroone.star.sale.mapper.SaleFormInfoMapper;
import com.zeroone.star.sale.mapper.SaleFormMapper;
import com.zeroone.star.sale.mapper.SaleInfoMapper;
import com.zeroone.star.sale.mapper.SaleMapper;
import com.zeroone.star.sale.service.SaleFormService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.SimpleDateFormat;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
public class SaleFormServiceImpl implements SaleFormService {

    @Resource
    private com.zeroone.star.sale.service.SaleDraftService saleDrafts;
    @Resource
    private com.zeroone.star.sale.service.SaleDocumentAccess saleAccess;
    @Resource
    private com.zeroone.star.sale.service.SalePostingService salePosting;

    @Resource
    private com.zeroone.star.sale.service.SaleSnapshotService snapshots;
    @Resource
    private com.zeroone.star.sale.service.SaleCheckService saleChecks;
    @Resource
    private SaleFormMapper saleFormMapper;

    @Resource
    private SaleFormInfoMapper saleFormInfoMapper;

    @Autowired
    private SaleMapper saleMapper;

    @Autowired
    private SaleInfoMapper saleInfoMapper;

    @Override
    @Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
    public JsonVO<PageDTO<SaleListDTO>> getSaleList(SaleQuery query) {
        query.setAuthorizedFrame(saleAccess.frame(saleAccess.authorize("/sale/form/getSaleList")));
        try {
            // 防止非法分页参数
            long pageIndex = query.getPageIndex() < 1 ? 1 : query.getPageIndex();
            long pageSize = query.getPageSize() < 1 ? 10 : Math.min(200, query.getPageSize());

            Page<SaleListDTO> mpPage = new Page<>(pageIndex, pageSize);
            Page<SaleListDTO> resultPage = saleFormMapper.selectSaleList(mpPage, query);

            Map<String,String> versions=snapshots.versions(resultPage.getRecords().stream().map(SaleListDTO::getId).collect(Collectors.toList()));
            for(SaleListDTO row:resultPage.getRecords())row.setVersion(versions.get(row.getId()));
            PageDTO<SaleListDTO> pageDTO = PageDTO.create(resultPage);
            return JsonVO.success(pageDTO);

        } catch (Exception e) {
            log.error("获取销售单列表失败", e);
            return JsonVO.fail(null);
        }
    }

    @Override
    public JsonVO<List<SaleDetailDTO>> getSaleDetail(String customer, LocalDateTime time, String number) {
        String allowedFrame = saleAccess.frame(saleAccess.authorize("/sale/form/getSaleDetail"));
        try {
            // 参数校验：至少需要一个查询条件
            if ((customer == null || customer.trim().isEmpty()) &&
                    time == null &&
                    (number == null || number.trim().isEmpty())) {
                return JsonVO.create(null, ResultStatus.PARAMS_INVALID.getCode(), "至少需要提供一个查询条件");
            }

            // 根据条件查询销售单详情
            List<SaleDetailDTO> saleDetails = saleFormInfoMapper.selectSaleDetailByCondition(customer, time, number, allowedFrame);
            if (saleDetails == null || saleDetails.isEmpty()) {
                return JsonVO.create(null, ResultStatus.FAIL.getCode(), "未找到对应的销售单详情");
            }

            return JsonVO.success(saleDetails);

        } catch (Exception e) {
            log.error("获取销售单详情失败, customer: {}, time: {}, number: {}", customer, time, number, e);
            return JsonVO.fail(null);
        }
    }

    @Override
    public JsonVO<SaleReturnGenerateDTO> getGenerateReturnData(String saleId) {
        try {
            if (saleId == null || saleId.trim().isEmpty()) {
                return JsonVO.create(null, ResultStatus.PARAMS_INVALID.getCode(), "销售单ID不能为空");
            }

            // 获取销售单基础信息 - 使用 selectSaleForReturn 方法
            SaleForm saleForm = saleFormMapper.selectSaleForReturn(saleId);
            if (saleForm == null) {
                return JsonVO.create(null, ResultStatus.FAIL.getCode(), "未找到对应的销售单");
            }

            // 基于销售单数据构建退货单数据
            SaleReturnGenerateDTO returnData = new SaleReturnGenerateDTO();
            BeanUtils.copyProperties(saleForm, returnData);

            // 设置退货单特定字段
            returnData.setSource(saleForm.getId()); // 关联原销售单
            returnData.setTime(LocalDateTime.now()); // 退货单时间为当前时间

            return JsonVO.success(returnData);

        } catch (Exception e) {
            log.error("获取销售退货单生成数据失败, saleId: {}", saleId, e);
            return JsonVO.fail(null);
        }
    }

    /**
     * 新增销售单
     * @param saleDTO 销售单数据
     */

    @Transactional(rollbackFor = Exception.class)
    @Override
    public void addSale(SaleDTO saleDTO) {
        saleDrafts.save(saleDTO, false);
    }

    /**
     * 修改销售单
     * @param saleDTO 销售单数据
     */

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateSale(SaleDTO saleDTO) {
        saleDrafts.save(saleDTO, true);
    }

    /**
     * 批量删除销售单
     * @param ids 销售单id
     * @return 删除的个数
     */

    @Transactional(rollbackFor = Exception.class)
    @Override
    public int batchDeleteSales(List<String> ids) {
        com.zeroone.star.project.components.user.UserDTO actor = saleAccess.authorize("/sale/form/deleteSales");
        if (ids == null || ids.isEmpty() || ids.size() > 200 || new HashSet<>(ids).size() != ids.size()) throw new IllegalArgumentException("请选择1到200张不同单据");
        saleDrafts.lockWrites();
        /// 先查询到ids列表中的所有销售单
        List<SaleDO> sales = saleMapper.selectBatchIds(ids);
        for (SaleDO current : sales) saleAccess.requireFrame(actor, current.getFrame());
        /// 把每一个销售单的详情id存入一个Map中
        Map<String,SaleDO> saleMap = new HashMap<>();
        for (SaleDO sale : sales) {
            saleMap.put(sale.getId(),sale);
        }
        /// 批量校验
        for (String id : ids) {
            SaleDO sale = saleMap.get(id);
            if(sale == null){
                throw new IllegalArgumentException("id:" + id + ",销售单不存在");
            }
            if(Boolean.TRUE.equals(sale.getExamine())){
                throw new IllegalArgumentException("id:" + id + ",销售单已审核,不能删除");
            }
            if(sale.getNucleus() != 0){
                throw new IllegalArgumentException("id:" + id + ",销售单已核销,不能删除");
            }
            salePosting.requireDeletable(id);
        }
        /// 执行批量删除 同时删除主表以及详情表有关的数据
        saleMapper.deleteBatchWithDetails(ids);

        /// 最终只返回删除主表的个数
        return ids.size();
    }

    /**
     * 核对/反核对销售单
     * @param ids 销售单id
     * @param check 核对/反核对
     * @return 核对/反核对个数
     */

    @Transactional(rollbackFor = Exception.class)
    @Override
    public Integer checkSales(com.zeroone.star.project.dto.j4.sale.SaleReviewCommand command, boolean check) {
        return saleChecks.check(command,check);
    }

    /**
     * 审核销售单
     * @param ids 销售单id
     * @param examine 审核/反审核
     * @return 审核/反审核个数
     */

    @Transactional(rollbackFor = Exception.class)
    @Override
    public Integer examineSales(com.zeroone.star.project.dto.j4.sale.SaleReviewCommand command, boolean examine) {
        return salePosting.post(command, examine);
    }

    /**
     * 计算销售单金额
     * @param sale 销售单
     * @param details 销售单详情
     */

}
