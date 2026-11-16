package com.zeroone.star.purchase.service.impl;
import cn.hutool.core.bean.BeanUtil;
import com.alibaba.excel.util.StringUtils;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.dto.j3.purchase.PurchaseOrderAddDTO;
import com.zeroone.star.project.dto.j3.purchase.PurchaseOrderInfoDTO;
import com.zeroone.star.project.dto.j3.purchase.PurchaseOrderUpdateDTO;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.purchase.DO.BorDO;
import com.zeroone.star.purchase.DO.BorInfoDO;
import com.zeroone.star.purchase.mapper.BorMapper;
import com.zeroone.star.purchase.service.IBorInfoService;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.purchase.*;
import com.zeroone.star.project.query.j3.purchase.PurchaseOrderQuery;
import com.zeroone.star.purchase.DO.BorDO;
import com.zeroone.star.purchase.DO.BorInfoDO;
import com.zeroone.star.purchase.DO.BuyDO;
import com.zeroone.star.purchase.DO.GoodsDO;
import com.zeroone.star.purchase.mapper.BorInfoMapper;
import com.zeroone.star.purchase.mapper.BorMapper;
import com.zeroone.star.purchase.mapper.BuyMapper;
import cn.hutool.core.date.DateTime;
import com.alibaba.excel.EasyExcel;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.dto.j3.purchase.GoodsDataDTO;
import com.zeroone.star.purchase.DO.BorDO;
import com.zeroone.star.purchase.DO.BorInfoDO;
import com.zeroone.star.purchase.DO.GoodsDO;
import com.zeroone.star.purchase.mapper.BorInfoMapper;
import com.zeroone.star.purchase.mapper.BorMapper;
import com.zeroone.star.purchase.mapper.GoodsMapper;
import com.zeroone.star.purchase.service.IBorService;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.SneakyThrows;
import com.alibaba.excel.ExcelWriter;
import com.alibaba.excel.write.metadata.WriteSheet;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.List;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * <p>
 * 采购订单 服务实现类
 * </p>
 *
 * @author 小夏
 * @since 2025-10-27
 */
@Service
public class BorServiceImpl extends ServiceImpl<BorMapper, BorDO> implements IBorService {
    @Resource
    private IBorInfoService borInfoService;
    @Resource
    private UserHolder userHolder;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseOrderDraftService orderDrafts;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseOrderAuditService orderAudit;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseDocumentAccess orderAccess;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseOrderDeleteService orderDeletes;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseOrderImportService orderImports;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseOrderExportService orderExports;
    @Resource private com.zeroone.star.purchase.service.PurchaseOrderListView orderListView;

    /**
     * 新增采购订单
     * @param purchaseOrderAddDTO
     * @return
     */
    @Transactional
    public JsonVO<String> addPurchaseOrder(PurchaseOrderAddDTO purchaseOrderAddDTO) {
        return JsonVO.success(orderDrafts.create(purchaseOrderAddDTO));
    }

    /**
     * 修改采购订单
     * @param purchaseOrderUpdateDTO
     * @return
     */
    @Override
    @Transactional
    public JsonVO<String> updatePurchaseOrder(PurchaseOrderUpdateDTO purchaseOrderUpdateDTO) {
        orderAudit.guardUpdate(purchaseOrderUpdateDTO);
        String id = purchaseOrderUpdateDTO.getId();

        BorDO bor = BeanUtil.copyProperties(purchaseOrderUpdateDTO, BorDO.class);
        List<PurchaseOrderInfoDTO> borInfoDTOList = purchaseOrderUpdateDTO.getPurchaseOrderInfoDTOList();

        // The existing creator and organization belong to the original document.
        // 修改采购订单
        updateById(bor);

        // 修改采购订单详情
        // 1、删除原始的采购订单详情信息
        QueryWrapper<BorInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("pid", id);
        borInfoService.remove(queryWrapper);
        // 2、插入新的采购订单详情信息
        ArrayList<BorInfoDO> borInfoList = new ArrayList<>();
        for (PurchaseOrderInfoDTO borInfoDTO : borInfoDTOList) {
            BorInfoDO borInfo = BeanUtil.copyProperties(borInfoDTO, BorInfoDO.class);
            borInfo.setPid(id);    // 设置所属id
            borInfoList.add(borInfo);
        }
        borInfoService.saveBatch(borInfoList);

        return JsonVO.success(id);
    }

    /**
     * 删除采购订单
     * @param ids
     * @return
     */
    @Transactional
    public JsonVO<String> deletePurchaseOrder(List<String> ids) {

        int deleted=orderDeletes.delete(ids);
        return JsonVO.success("已删除"+deleted+"张采购订单草稿");
    }

    /**
     * 获取采购订单列表(条件+分页)
     * @Author 待兼唐怀瑟
     * @param query
     * @return
     */
    @Override
    @Transactional(readOnly=true)
    public PageDTO<PurchaseOrderListDTO> listPurchaseOrders(PurchaseOrderQuery query) {
        if(query.getPageSize()<1 || query.getPageSize()>200 || query.getPageIndex()<1)throw new IllegalArgumentException("页码必须大于0，每页1到200条");
        String allowedFrame=orderAccess.frame(orderAccess.authorize("/purchase-order/list"));
        // 分页插件对象
        IPage<BorDO> ipage = new Page<>(query.getPageIndex(), query.getPageSize());

        // 条件
        LambdaQueryWrapper<BorDO> w = new LambdaQueryWrapper<>();
        if(allowedFrame!=null)w.eq(BorDO::getFrame,allowedFrame);
        w.likeRight(StringUtils.isNotBlank(query.getNumber()), BorDO::getNumber, query.getNumber());
        if(StringUtils.isNotBlank(query.getSupplier()))w.apply("(supplier={0} OR EXISTS(SELECT 1 FROM supplier s WHERE s.id=bor.supplier AND s.name LIKE {1}))",query.getSupplier(),"%"+query.getSupplier()+"%");
        if(StringUtils.isNotBlank(query.getPeople()))w.apply("(people={0} OR EXISTS(SELECT 1 FROM people p WHERE p.id=bor.people AND p.name LIKE {1}))",query.getPeople(),"%"+query.getPeople()+"%");
        if(StringUtils.isNotBlank(query.getUser()))w.apply("(`user`={0} OR EXISTS(SELECT 1 FROM `user` u WHERE u.id=bor.`user` AND u.name LIKE {1}))",query.getUser(),"%"+query.getUser()+"%");
        if(StringUtils.isNotBlank(query.getExamine()))w.eq(BorDO::getExamine,com.zeroone.star.purchase.service.PurchaseOrderListView.filter(query.getExamine(),true));
        if(StringUtils.isNotBlank(query.getState()))w.eq(BorDO::getState,com.zeroone.star.purchase.service.PurchaseOrderListView.filter(query.getState(),false));
        if(StringUtils.isNotBlank(query.getName()))w.apply("EXISTS(SELECT 1 FROM bor_info i JOIN goods g ON g.id=i.goods WHERE i.pid=bor.id AND g.name LIKE {0})","%"+query.getName()+"%");
        w.like(StringUtils.isNotBlank(query.getData()),BorDO::getData,query.getData());

        DateTimeFormatter fmt = DateTimeFormatter.ISO_LOCAL_DATE;
        if(StringUtils.isNotBlank(query.getDocumentStartTime()) && StringUtils.isNotBlank(query.getDocumentEndTime()) && LocalDate.parse(query.getDocumentStartTime()).isAfter(LocalDate.parse(query.getDocumentEndTime())))throw new IllegalArgumentException("单据开始日期不能晚于结束日期");
        if(StringUtils.isNotBlank(query.getArrivalStartTime()) && StringUtils.isNotBlank(query.getArrivalEndTime()) && LocalDate.parse(query.getArrivalStartTime()).isAfter(LocalDate.parse(query.getArrivalEndTime())))throw new IllegalArgumentException("到货开始日期不能晚于结束日期");
        if (StringUtils.isNotBlank(query.getDocumentStartTime())) {
            LocalDateTime start = LocalDate.parse(query.getDocumentStartTime(), fmt).atStartOfDay();
            w.ge(BorDO::getTime, start);
        }
        if (StringUtils.isNotBlank(query.getDocumentEndTime())) {
            LocalDateTime end = LocalDate.parse(query.getDocumentEndTime(), fmt).atTime(23, 59, 59);
            w.le(BorDO::getTime, end);
        }
        if (StringUtils.isNotBlank(query.getArrivalStartTime())) {
            LocalDateTime start = LocalDate.parse(query.getArrivalStartTime(), fmt).atStartOfDay();
            w.ge(BorDO::getArrival, start);
        }
        if (StringUtils.isNotBlank(query.getArrivalEndTime())) {
            LocalDateTime end = LocalDate.parse(query.getArrivalEndTime(), fmt).atTime(23, 59, 59);
            w.le(BorDO::getArrival, end);
        }
        w.orderByDesc(BorDO::getTime).orderByAsc(BorDO::getId);

        // 执行分页
        ipage = this.page(ipage, w);

        return orderListView.enrich(PageDTO.create((Page<BorDO>)ipage, PurchaseOrderListDTO.class),ipage.getRecords());
    }

    @Resource
    private BorInfoMapper borInfoMapper;
    @Resource
    private GoodsMapper goodsMapper;
    @Resource
    private BuyMapper buyMapper;

    /**
     * 获取指定采购订单详情
     * @Author 待兼唐怀瑟
     * @param id
     * @return
     */
    @Override
    public PurchaseOrderDetailDTO getPurchaseOrderDetail(String id) {
        orderAudit.document(id);
        BorDO bor = this.getById(id);
        if (bor == null) throw new RuntimeException("单据不存在");

        PurchaseOrderDetailDTO dto = new PurchaseOrderDetailDTO();

        // 采购订单详情
        List<BorInfoDO> infoList = borInfoMapper.selectList(
                new LambdaQueryWrapper<BorInfoDO>().eq(BorInfoDO::getPid, id)
                        .last("LIMIT 1"));
        if (!infoList.isEmpty()) {
            BorInfoDO info = infoList.get(0);
            GoodsDO g = goodsMapper.selectById(info.getGoods());

            dto.setGoods(info.getGoods());      // 商品编号
            dto.setName(g == null ? "" : g.getName()); // 商品名称
            dto.setSpec(g == null ? "" : g.getSpec()); // 规格型号
            dto.setAttr(info.getAttr());        // 辅助属性
            dto.setWarehouse(info.getWarehouse()); // 仓库
            dto.setUnit(info.getUnit());        // 单位
            dto.setPrice(info.getPrice().toPlainString()); // 单价
            dto.setNums(info.getNums().toPlainString());   // 数量
            dto.setHandle(info.getHandle().toPlainString());// 入库数量
            dto.setAmount(info.getTotal().toPlainString()); // 金额
            dto.setTax(info.getTax().toPlainString());      // 税率(%)
            dto.setTat(info.getTat().toPlainString());      // 税额
            dto.setTpt(info.getTpt().toPlainString());      // 价税合计
            dto.setData(info.getData());        // 备注信息（明细）
        }

        //抬头字段
        PurchaseOrderOtherDetailDTO header = new PurchaseOrderOtherDetailDTO();
        header.setSupplier(bor.getSupplier());   // 供应商
        header.setTime(bor.getTime().toLocalDate().toString()); // 单据日期
        header.setNumber(bor.getNumber());       // 单据编号
        header.setTotal(bor.getTotal().toPlainString()); // 单据金额
        header.setActual(bor.getActual().toPlainString()); // 实际金额
        header.setPeople(bor.getPeople());       // 关联人员
        header.setArrivalTime(bor.getArrival() == null ? "" : bor.getArrival().toLocalDate().toString()); // 到货日期
        header.setLogistics(bor.getLogistics()); // 物流信息
        header.setFile(bor.getFile());           // 单据附件
        header.setData(bor.getData());           // 备注信息（主单）

        dto.setPurchaseOrderOtherDetailDTO(header);
        return dto;
    }

    /**
     * 审核/反审核(支持批量)
     * @Author 待兼唐怀瑟
     * @param dto
     * @return
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public List<String> batchApprovePurchaseOrders(AuditRequestDTO dto) {
        return orderAudit.audit(dto);
    }
    @Resource
    EasyExcelComponent excel;

    @Resource
    BorMapper borMapper;

    /**
     * 导出简单报表
     * @author 小王
     * @param ids 采购订单ID列表
     * @return
     */
    @Override
    public ResponseEntity<byte[]> exportBor(List<String> ids) {
        return ResponseEntity.ok().header("Content-Disposition","attachment; filename=purchase-orders.xlsx")
                .header("Content-Type","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                .header("Cache-Control","no-store").body(orderExports.simple(ids));
    }

    /**
     * 导入数据
     * @author 小王
     * @param file Excel文件
     * @return 导入结果
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public Boolean importBor(MultipartFile file) {
        try { orderImports.importFile(file); return true; }
        catch (java.io.IOException error) { throw new IllegalArgumentException("Excel文件无法读取，请使用下载的模板",error); }
    }

    /**
     * 获取Excel单元格值
     */
    private String getCellValue(Map<Integer, String> row, int columnIndex) {
        String value = row.get(columnIndex);
        return value != null ? value.trim() : "";
    }

    /**
     * 解析BigDecimal
     */
    private BigDecimal parseBigDecimal(String value) {
        if (!org.springframework.util.StringUtils.hasText(value)) {
            return null;
        }
        try {
            return new BigDecimal(value.trim());
        } catch (Exception e) {
            return null;
        }
    }
}
