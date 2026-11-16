package com.zeroone.star.storemanagement.service.impl;

import cn.hutool.core.date.DateTime;
import cn.hutool.core.lang.Snowflake;
import cn.hutool.core.util.IdUtil;
import com.alibaba.cloud.commons.lang.StringUtils;
import com.alibaba.excel.EasyExcel;
import com.alibaba.excel.ExcelWriter;
import com.alibaba.excel.write.metadata.WriteSheet;
import com.alibaba.excel.write.metadata.fill.FillConfig;
import com.alibaba.fastjson.JSON;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.project.components.easyexcel.ExcelReadListener;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j2.store.*;
import com.zeroone.star.project.query.j2.store.OtherInQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.convertor.EntryConverter;
import com.zeroone.star.storemanagement.convertor.MsEntryMapper;
import com.zeroone.star.storemanagement.entity.*;
import com.zeroone.star.storemanagement.mapper.*;
import com.zeroone.star.storemanagement.service.IOtherInService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;
import java.util.zip.Deflater;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

@Service
@Slf4j
public class OtherInServiceImpl extends ServiceImpl<OtherInMapper, EntryDO>  implements IOtherInService {

    @Resource
    OtherInMapper otherInMapper;

    @Resource
    OtherInInfoMapper otherInInfoMapper;

    @Resource
    CostMapper costMapper;

    @Resource
    LogMapper logMapper;

    @Resource
    RecordMapper recordMapper;

    @Resource
    RoomMapper roomMapper;

    @Resource
    RoomInfoMapper roomInfoMapper;

    @Resource
    private MsEntryMapper msEntryMapper;

    @Resource
    SummaryMapper summaryMapper;

    @Resource
    ServeMapper serveMapper;

    @Resource
    ServeInfoMapper serveInfoMapper;

    @Resource
    OtherInListMapper otherInListMapper;

    @Resource
    private UserHolder userHolder;

    @Resource
    EntryConverter entryConverter;

    @Resource
    private GoodsMapper goodsMapper;

    @Resource
    private FrameMapper frameMapper;

    @Resource
    private PeopleMapper peopleMapper;

    @Resource
    private UserMapper userMapper;

    @Resource
    private SupplierMapper supplierMapper;

    @Resource
    private BatchMapper batchMapper;

    @Resource
    private BatchInfoMapper batchInfoMapper;

    @Resource
    private WarehouseMapper warehouseMapper;

    @Resource
    private org.springframework.jdbc.core.JdbcTemplate stockDb;
    @Resource
    private com.zeroone.star.storemanagement.service.StockDocumentAccess stockAccess;
    @Resource
    private com.zeroone.star.storemanagement.service.StockDocumentWriteLock stockWriteLock;

    @Resource
    private com.zeroone.star.storemanagement.service.WarehouseReportDocumentService reportDocuments;

    //雪花算法
    private final Snowflake snowflake = IdUtil.getSnowflake();
    @Autowired
    private ThreadPoolTaskExecutor threadPoolTaskExecutor;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateOtherInList(OtherInListDetailDTO dto) {
        UserDTO actor = stockAccess.authorize("entry", "save");
        if (dto == null || dto.getId() == null) throw new IllegalArgumentException("单据ID不能为空");
        stockWriteLock.lock("entry");
        List<Map<String, Object>> found = stockDb.queryForList("SELECT * FROM entry WHERE id=? FOR UPDATE", dto.getId());
        if (found.size() != 1) throw new IllegalArgumentException("单据不存在");
        Map<String, Object> original = found.get(0);
        stockAccess.creationFrame(actor, String.valueOf(original.get("frame")));
        if (Boolean.TRUE.equals(original.get("examine")) || "1".equals(String.valueOf(original.get("examine"))))
            throw new IllegalStateException("已审核单据不能修改，请先反审核");
        if (Boolean.TRUE.equals(original.get("check")) || "1".equals(String.valueOf(original.get("check"))))
            throw new IllegalStateException("已核对单据不能修改，请先反核对");
        if(stockDb.queryForObject("SELECT COUNT(*) FROM period WHERE date>=CAST(? AS DATE)",Integer.class,original.get("time"))>0)
            throw new IllegalStateException("已结账期间的入库单不能修改");
        if (dto.getVersion() == null || !dto.getVersion().equals(reportDocuments.lockedVersion("entry", dto.getId())))
            throw new IllegalStateException("单据已被其他操作修改，请重新打开详情");
        if (stockDb.queryForObject("SELECT COUNT(*) FROM cost WHERE `class`=? AND type='entry' AND (settle<>0 OR state<>0)", Integer.class, dto.getId()) > 0)
            throw new IllegalStateException("单据已有费用结算，不能重写费用明细");
        prepareDraft(dto, actor, dto.getId());
        EntryDO head = msEntryMapper.addDtoToEntry(dto);
        head.setId(dto.getId());
        head.setUser(String.valueOf(original.get("user")));
        if (otherInMapper.updateById(head) != 1) throw new IllegalStateException("单据修改失败");
        otherInInfoMapper.deleteByPid(dto.getId());
        stockDb.update("DELETE FROM cost WHERE `class`=? AND type='entry'", dto.getId());
        persistDetails(dto.getId(), dto);
        persistOperation(dto.getId(), actor, "修改入库单");
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public JsonVO<String> saveOtherInList(OtherInListAddDTO dto) {
        UserDTO actor = stockAccess.authorize("entry", "create");
        prepareDraft(dto, actor, null);
        EntryDO head = msEntryMapper.addDtoToEntry(dto);
        String id = IdUtil.fastSimpleUUID();
        head.setId(id);
        if (otherInMapper.insert(head) != 1) throw new IllegalStateException("入库单保存失败");
        persistDetails(id, dto);
        persistOperation(id, actor, "新增入库单");
        return JsonVO.success(id);
    }

    private void prepareDraft(OtherInListAddDTO dto, UserDTO actor, String excludedId) {
        if (dto == null) throw new IllegalArgumentException("单据不能为空");
        dto.setUser(actor.getId());
        dto.setFrame(stockAccess.creationFrame(actor, dto.getFrame()));
        String invalid = validate(dto);
        if (invalid != null) throw new IllegalArgumentException(invalid);
        if (dto.getExamine() != 0 || dto.getCheck() != 0)
            throw new IllegalArgumentException("新单据必须先保存为未审核、未核对的草稿");
        if (dto.getOtherInListDetailInfoDTOList() == null || dto.getOtherInListDetailInfoDTOList().isEmpty())
            throw new IllegalArgumentException("入库单明细不能为空");
        String number = dto.getNumber().trim();
        if (number.codePointCount(0, number.length()) > 32) throw new IllegalArgumentException("单据编号最多32个字符");
        stockWriteLock.lock("entry");
        if (!stockDb.queryForList("SELECT id FROM entry WHERE number=? AND id<>? FOR UPDATE", number, excludedId == null ? "" : excludedId).isEmpty())
            throw new IllegalArgumentException("单据编号已存在");
        dto.setNumber(number);
        BigDecimal total = BigDecimal.ZERO;
        for (OtherInListDetailInfoDTO item : dto.getOtherInListDetailInfoDTOList()) {
            if (item == null || item.getGoods() == null || item.getWarehouse() == null || item.getUnit() == null || item.getUnit().trim().isEmpty())
                throw new IllegalArgumentException("明细中的商品、仓库和单位不能为空");
            if (stockDb.queryForObject("SELECT COUNT(*) FROM goods WHERE id=?", Integer.class, item.getGoods()) != 1 ||
                    stockDb.queryForObject("SELECT COUNT(*) FROM warehouse WHERE id=?", Integer.class, item.getWarehouse()) != 1)
                throw new IllegalArgumentException("商品或仓库不存在");
            com.zeroone.star.storemanagement.service.WarehouseScope.require(stockDb,dto.getFrame(),item.getWarehouse());
            Map<String,Object> units=stockDb.queryForMap("SELECT unit,units FROM goods WHERE id=?",item.getGoods());
            String baseUnit=String.valueOf(units.get("unit"));
            if("-1".equals(baseUnit)){
                cn.hutool.json.JSONArray choices=new cn.hutool.json.JSONArray(String.valueOf(units.get("units")));
                if(choices.isEmpty())throw new IllegalArgumentException("商品缺少基础单位配置");
                baseUnit=choices.getJSONObject(0).getStr("source");
            }
            if(baseUnit==null || !baseUnit.equals(item.getUnit()))throw new IllegalArgumentException("其他入库必须使用商品的基础单位，请重新选择商品并核对数量");
            if (item.getNums() == null || item.getNums().signum() <= 0 || item.getPrice() == null || item.getPrice().signum() < 0)
                throw new IllegalArgumentException("数量必须大于零，单价不能为负数");
            try {
                item.setNums(item.getNums().setScale(4, java.math.RoundingMode.UNNECESSARY));
                item.setPrice(item.getPrice().setScale(4, java.math.RoundingMode.UNNECESSARY));
            } catch (ArithmeticException error) { throw new IllegalArgumentException("数量和单价最多保留4位小数"); }
            BigDecimal amount = item.getNums().multiply(item.getPrice()).setScale(4, java.math.RoundingMode.HALF_UP);
            if (item.getNums().precision() > 12 || item.getPrice().precision() > 12 || amount.precision() > 12)
                throw new IllegalArgumentException("明细数量、单价或金额超过允许范围");
            item.setTotal(amount);
            total = total.add(amount);
        }
        dto.setTotal(total);
        List<CostDTO> fees = dto.getCostDTOList() == null ? Collections.emptyList() : dto.getCostDTOList();
        BigDecimal feeTotal = BigDecimal.ZERO;
        for (CostDTO fee : fees) {
            if (fee == null || fee.getMoney() == null || fee.getMoney().signum() < 0 || fee.getIet() == null ||
                    stockDb.queryForObject("SELECT COUNT(*) FROM iet WHERE id=?", Integer.class, fee.getIet()) != 1)
                throw new IllegalArgumentException("费用金额或收支类别无效");
            feeTotal = feeTotal.add(fee.getMoney());
        }
        if (feeTotal.compareTo(dto.getCost()) != 0) throw new IllegalArgumentException("费用总额与费用明细不一致");
    }

    private void persistDetails(String id, OtherInListAddDTO dto) {
        List<CostDTO> fees = dto.getCostDTOList() == null ? Collections.emptyList() : dto.getCostDTOList();
        for (OtherInListDetailInfoDTO item : dto.getOtherInListDetailInfoDTOList()) {
            EntryInfoDO detail = msEntryMapper.addDetailDtoToEntryInfo(item);
            detail.setId(IdUtil.fastSimpleUUID());
            detail.setPid(id);
            if (detail.getAttr() == null) detail.setAttr("");
            if (detail.getSerial() == null) detail.setSerial("[]");
            otherInInfoMapper.insertByOne(detail);
        }
        for (CostDTO fee : fees) {
            stockDb.update("INSERT INTO cost(id,type,`class`,time,iet,money,data,settle,state) VALUES(?,'entry',?,?,?,?,?,0,0)",
                IdUtil.fastSimpleUUID(), id, dto.getTime(), fee.getIet(), fee.getMoney(), fee.getData());
        }
    }

    private void persistOperation(String id, UserDTO actor, String action) {
        stockDb.update("INSERT INTO `log`(id,time,`user`,info) VALUES(?,?,?,?)", IdUtil.fastSimpleUUID(), LocalDateTime.now(), actor.getId(), action + "[" + id + "]");
        stockDb.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'entry',?,?,?,?)", IdUtil.fastSimpleUUID(), id, LocalDateTime.now(), actor.getId(), action);
    }

    /**
     * 数据合法性校验
     */
    private String validate(OtherInListAddDTO dto) {
        if (dto == null) {
            return "参数不能为空";
        }

        // 必填字段校验
        if (dto.getTime() == null) {
            return "单据日期不能为空";
        }
        if (StringUtils.isBlank(dto.getNumber())) {
            return "单据编号不能为空";
        }
        if (dto.getType() == null) {
            return "单据类型不能为空";
        }
        if (dto.getTotal() == null) {
            return "单据成本不能为空";
        }
        if (dto.getCost() == null) {
            return "单据费用不能为空";
        }
        if (dto.getExamine() == null) {
            return "审核状态不能为空";
        }
        if (dto.getCse() == null) {
            return "费用状态不能为空";
        }
        if (dto.getCheck() == null) {
            return "核对状态不能为空";
        }
        if (dto.getUser() == null) {
            return "制单人不能为空";
        }

        // 数值范围校验
        if (dto.getTotal().compareTo(BigDecimal.ZERO) < 0) {
            return "单据成本不能为负数";
        }
        if (dto.getCost().compareTo(BigDecimal.ZERO) < 0) {
            return "单据费用不能为负数";
        }
        if (dto.getType() != 0 && dto.getType() != 1) {
            return "单据类型只能是0(其它入库单)或1(盘盈单)";
        }
        if (dto.getExamine() != 0 && dto.getExamine() != 1) {
            return "审核状态只能是0(未审核)或1(已审核)";
        }
        if (dto.getCse() < 0 || dto.getCse() > 3) {
            return "费用状态范围错误";
        }
        if (dto.getCheck() != 0 && dto.getCheck() != 1) {
            return "核对状态只能是0(未核对)或1(已核对)";
        }

        // 业务逻辑校验
        if (dto.getTime().isAfter(LocalDateTime.now())) {
            return "单据日期不能晚于当前时间";
        }

//        OtherInListInfoDTO otherInListInfoDTO = (OtherInListInfoDTO) dto.getOtherInListDetailInfoDTOList();
//        // 关联数据校验
//        if (validateOtherInListInfo(otherInListInfoDTO) == null) {
//            return "入库单详细信息不能为空";
//        }
//        if (validateCost((CostDTO) dto.getCostDTOList()) == null) {
//            return "单据费用列表不能为空";
//        }

        return null; // 返回null表示校验通过
    }

    /**
     * 入库单详细信息校验
     */
    private String validateOtherInListInfo(OtherInListInfoDTO info) {
        if (info == null) {
            return "入库单详细信息不能为空";
        }

        // 必填字段校验
//        if (StringUtils.isBlank(info.getName())) {
//            return "商品名称不能为空";
//        }
//        if (StringUtils.isBlank(info.getNumber())) {
//            return "商品编号不能为空";
//        }
        if (Integer.parseInt(info.getGoods()) <= 0) {
            return "所属商品ID无效";
        }

        if (StringUtils.isBlank(info.getUnit())) {
            return "单位不能为空";
        }
        if (Integer.parseInt(info.getWarehouse()) <= 0) {
            return "仓库ID无效";
        }

        // 数值范围校验
        if (info.getPrice().compareTo(BigDecimal.ZERO) < 0) {
            return "商品成本不能为负数";
        }
        if (info.getNums().compareTo(BigDecimal.ZERO) <= 0) {
            return "商品数量必须大于0";
        }
        if (info.getTotal().compareTo(BigDecimal.ZERO) < 0) {
            return "商品总成本不能为负数";
        }

        // 业务逻辑校验
        if (info.getMfd() != null && info.getMfd().isAfter(LocalDateTime.now())) {
            return "生产日期不能晚于当前时间";
        }

        // 计算一致性校验
        BigDecimal expectedTotal = info.getPrice().multiply(info.getNums());
        if (info.getTotal().subtract(expectedTotal).abs().compareTo(BigDecimal.valueOf(0.01)) > 0) {
            return String.format("商品总成本计算错误，应为%.4f", expectedTotal);
        }

        return null; // 返回null表示校验通过
    }

    /**
     * 费用信息校验
     */
    private String validateCost(CostDTO cost) {
        if (cost == null) {
            return "费用信息不能为空";
        }
        if (cost.getMoney().compareTo(BigDecimal.ZERO) < 0) {
            return "费用金额不能为负数";
        }
        return null;
    }

    @Override
    @Transactional
    public JsonVO<String> importExcel(MultipartFile file) {
        InputStream is = null;
        try {
            is = file.getInputStream();
        } catch (IOException e) {
            return JsonVO.fail(e.toString());
        }
        ExcelReadListener<OtherInImportExcelDTO> listener = new ExcelReadListener<>();
        EasyExcel.read(is, OtherInImportExcelDTO.class, listener).sheet().headRowNumber(2).doRead();
        List<OtherInImportExcelDTO> dataList = listener.getDataList();
        if(dataList == null){
            return JsonVO.fail("excel表中没有数据");
        }
        EntryDO entryDO = msEntryMapper.otherInImportExcelDTOToEntryDO(dataList.get(0));

        // 数据校验
        // 供应商不存在
        QueryWrapper<SupplierDO> wrapper2 = new QueryWrapper<>();
        wrapper2.lambda().eq(SupplierDO::getName, entryDO.getSupplier());
        SupplierDO supplierDO = supplierMapper.selectOne(wrapper2);
        if(supplierDO == null){
            return JsonVO.fail("供应商数据异常: " + entryDO.getSupplier());
        }
        // 日期校验
        LocalDate localDate = null;
        try {
            localDate = LocalDate.parse(dataList.get(0).getTime());
        } catch (Exception e) {
            return JsonVO.fail("单据日期异常: " + dataList.get(0).getTime());
        }
        LocalDateTime localDateTime = localDate.atTime(0, 0, 0);

        //people数据库中不存在
        QueryWrapper<PeopleDO> wrapper1 = new QueryWrapper<>();
        wrapper1.lambda().eq(PeopleDO::getName, dataList.get(0).getPeople());
        PeopleDO peopleDO = peopleMapper.selectOne(wrapper1);
        if(peopleDO==null){
            if(dataList.get(0).getPeople()!=null) return JsonVO.fail("关联人员在库中不存在");
            else peopleDO = new PeopleDO();
        }
        // 单据编号不能重复或为空
        if(dataList.get(0).getNumber().isEmpty()){
            return JsonVO.fail("单据编号未填写");
        }
        List<EntryDO> entryDOList = this.lambdaQuery().eq(EntryDO::getNumber, dataList.get(0).getNumber()).list();
        if(!entryDOList.isEmpty()){
            return JsonVO.fail("单据编号已存在: " + entryDO.getNumber());
        }
        // excel标红字段不能为空
        if(entryDO.getType()==-1){
            return JsonVO.fail("单据类型异常: " + dataList.get(0).getType());
        }

        // 数据填充
        entryDO.setSupplier(supplierDO.getId());
        entryDO.setPeople(peopleDO.getId());
        entryDO.setTime(localDateTime);
        entryDO.setCost(new BigDecimal(0));
        entryDO.setFile(null);
        entryDO.setMore(null);
        entryDO.setExamine(0);
        entryDO.setCse(0); //TODO: 未确定
        entryDO.setCheck(0);
        try {
//            String frameId = userHolder.getCurrentUser().getFrameId();
//            String userId = userHolder.getCurrentUser().getId();
            String frameId = "F001";
            String userId = "1";
            entryDO.setFrame(frameId);
            entryDO.setUser(userId);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
        otherInMapper.insert(entryDO);

        List<EntryInfoDO> entryInfoDOList = msEntryMapper.otherInImportExcelDTOListToEntryInfoDOList(dataList);
        for(int i=0; i<entryInfoDOList.size(); i++) {
            EntryInfoDO entryInfoDO = entryInfoDOList.get(i);
            // 数据校验
            // 商品不在库中
            QueryWrapper<GoodsDO> wrapper3 = new QueryWrapper<>();
            wrapper3.lambda().eq(GoodsDO::getName, dataList.get(i).getGoods());
            GoodsDO goodsDO = goodsMapper.selectOne(wrapper3);
            if(goodsDO == null){
                throw new RuntimeException("商品不存在: " + dataList.get(i).getGoods());
//                return JsonVO.fail("商品不存在: " + entryInfoDO.getGoods());
            }
            //仓库不在数据库中
            QueryWrapper<WarehouseDO> wrapper4 = new QueryWrapper<>();
            wrapper4.lambda().eq(WarehouseDO::getName, dataList.get(i).getWarehouse());
            WarehouseDO warehouseDO = warehouseMapper.selectOne(wrapper4);
            if(warehouseDO == null){
                throw new RuntimeException("仓库不存在: " + dataList.get(i).getWarehouse());
//                return JsonVO.fail("仓库不存在: " + entryInfoDO.getWarehouse());
            }
            // 校验日期格式
            LocalDate time = null;
            try {
                time = LocalDate.parse(dataList.get(i).getMfd());
            } catch (Exception e) {
                throw new RuntimeException("生产日期格式错误: " + dataList.get(i).getMfd());
//                return JsonVO.fail("生产日期格式错误: " + dataList.get(i).getMfd());
            }
            // 成本
            if(entryInfoDO.getPrice()==null){
                throw new RuntimeException("成本为空");
//                return JsonVO.fail("必填数据缺失");
            }
            // 数量
            if(entryInfoDO.getNums()==null){
                throw new RuntimeException("数量为空");
            }

            // 填充数据
            entryInfoDO.setPid(entryDO.getId());
            entryInfoDO.setGoods(goodsDO.getId());
            entryInfoDO.setWarehouse(warehouseDO.getId());
            entryInfoDO.setMfd(time);
        }
        otherInInfoMapper.insertBatch(entryInfoDOList);

        return JsonVO.success(entryDO.getId());
    }

    @Override
    public JsonVO<ResponseEntity<byte[]>> exportEasyExcel(String ids) {
        List<String> idList = Arrays.asList(ids.split("\\+"));
        if(idList.isEmpty()){
            throw new RuntimeException("未传入有效id");
        }
        List<EntryDO> entryDOList = this.lambdaQuery()
                .in(EntryDO::getId, idList)
                .list();
        List<OtherInEasyExportExcelDTO> otherInEasyExportExcelDTOList = msEntryMapper.entryDOListToOtherInEasyExportExcelDTOList(entryDOList);
        Integer sumNum = otherInEasyExportExcelDTOList.size();
        BigDecimal sumTotal = new BigDecimal(0);
        BigDecimal sumCost = new BigDecimal(0);

        for(int i=0; i<sumNum; i++){
            //frame
            FrameDO frameDO = frameMapper.selectById(entryDOList.get(i).getFrame());
            if(frameDO==null){
                frameDO = new FrameDO();
            }
            String frameCv = frameDO.getName();
            otherInEasyExportExcelDTOList.get(i).setFrameCv(frameCv);

            // supplier
            SupplierDO supplierDO = supplierMapper.selectById(entryDOList.get(i).getSupplier());
            if(supplierDO == null){
                supplierDO = new SupplierDO();
            }
            otherInEasyExportExcelDTOList.get(i).setSupplierCv(supplierDO.getName());

            //type
            String typeCv = null;
            if(entryDOList.get(i).getType()==0) typeCv = "其他入库单";
            else if(entryDOList.get(i).getType()==1) typeCv = "盘盈单";
            else {
                throw new RuntimeException("单据类型异常");
            }
            otherInEasyExportExcelDTOList.get(i).setTypeCv(typeCv);

            // time
            String timeCv = entryDOList.get(i).getTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            otherInEasyExportExcelDTOList.get(i).setTimeCv(timeCv);

            // people
            PeopleDO peopleDO = peopleMapper.selectById(entryDOList.get(i).getPeople());
            if(peopleDO == null) peopleDO = new PeopleDO();
            String peopleCv = peopleDO.getName();
            otherInEasyExportExcelDTOList.get(i).setPeopleCv(peopleCv);

            // examine
            String examineCv = null;
            if(entryDOList.get(i).getExamine() == 0) examineCv = "未审核";
            else if(entryDOList.get(i).getExamine() == 1) examineCv = "已审核";
            else {
                throw new RuntimeException("审核状态异常");
            }
            otherInEasyExportExcelDTOList.get(i).setExamineCv(examineCv);

            // cse
            String cseCv = null;
            if(entryDOList.get(i).getCse() == 0) cseCv = "未结算";
            else if(entryDOList.get(i).getCse() == 1) cseCv = "部分结算";
            else if(entryDOList.get(i).getCse() == 2) cseCv = "已结算";
            else if(entryDOList.get(i).getCse() == 3) cseCv = "无需结算";
            else {
                throw new RuntimeException("费用状态异常");
            }
            otherInEasyExportExcelDTOList.get(i).setCseCv(cseCv);

            // check
            String checkCv = null;
            if(entryDOList.get(i).getCheck() == 0) checkCv = "未核对";
            else if(entryDOList.get(i).getCheck() == 1) checkCv = "已核对";
            else {
                throw new RuntimeException("核对状态异常");
            }
            otherInEasyExportExcelDTOList.get(i).setCheckCv(checkCv);

            // user
            UserDO userDO = userMapper.selectById(entryDOList.get(i).getUser());
            if(userDO==null) userDO = new UserDO();
            String userCv = userDO.getName();
            otherInEasyExportExcelDTOList.get(i).setUserCv(userCv);

            sumTotal = sumTotal.add(entryDOList.get(i).getTotal());
            sumCost = sumCost.add(entryDOList.get(i).getCost());
        }

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        InputStream is = null;
        try {
            is = new ClassPathResource("templates/easyExcelTemplate.xlsx").getInputStream();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        ExcelWriter workBook = EasyExcel.write(baos, OtherInEasyExportExcelDTO.class).withTemplate(is).build();
        WriteSheet sheet = EasyExcel.writerSheet().build();
        Map<String, String> map = new HashMap<>();
        FillConfig build = FillConfig.builder().forceNewRow(true).build();

        map.put("sumNum", sumNum.toString());
        map.put("sumTotal", sumTotal.toString());
        map.put("sumCost", sumCost.toString());

        workBook.fill(otherInEasyExportExcelDTOList, build, sheet);
        workBook.fill(map, build, sheet);
        workBook.finish();
        byte[] byteArray = baos.toByteArray();
        HttpHeaders headers = new HttpHeaders();
        String filename = "OtherIn_"+ DateTime.now().toString("yyyyMMddHHmmssS") + ".xlsx";
        headers.setContentDispositionFormData("attachment", filename);
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        return JsonVO.success(new ResponseEntity<>(byteArray, headers, HttpStatus.OK));
    }

    @Override
    public JsonVO<ResponseEntity<byte[]>> exportDetailExcel(String ids) {
        List<String> idList = Arrays.asList(ids.split("\\+"));
        if(idList==null){
            throw new RuntimeException("id传入异常");
        }
        List<EntryDO> entryDOList = this.lambdaQuery()
                .in(EntryDO::getId, idList)
                .list();

        // 字节流
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        // 压缩包
        ZipOutputStream zos = new ZipOutputStream(baos);
        zos.setLevel(Deflater.BEST_COMPRESSION);

        // 遍历Entry表，生成zip
        for (EntryDO entryDO : entryDOList) {
            // 查找对应的entry_info和goods表，组装成otherInDetailExportExcelList
            QueryWrapper<EntryInfoDO> wrapper = new QueryWrapper<>();
            wrapper.lambda().eq(EntryInfoDO::getPid, entryDO.getId());
            List<EntryInfoDO> entryInfoDOList = otherInInfoMapper.selectList(wrapper);
            List<OtherInDetailExportExcelDTO> otherInDetailExportExcelList = entryInfoDOList.stream()
                    .map(entryInfoDO -> {
                        OtherInDetailExportExcelDTO otherInDetailExportExcel = msEntryMapper.entryInfoDOToOtherInDetailExportExcel(entryInfoDO);
                        GoodsDO goodsDO = goodsMapper.selectById(entryInfoDO.getGoods());
                        if(goodsDO==null) goodsDO = new GoodsDO();
                        otherInDetailExportExcel.setGoodName(goodsDO.getName());
                        otherInDetailExportExcel.setSpec(goodsDO.getSpec());
                        return otherInDetailExportExcel;
                    })
                    .collect(Collectors.toList());

            try {
                zos.putNextEntry(new ZipEntry(entryDO.getId().toString()+".xlsx"));
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            // 模板
            InputStream is = null;
            try {
                is = new ClassPathResource("templates/detailExcelTemplate.xlsx").getInputStream();
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
            ExcelWriter workBook = EasyExcel.write(zos, OtherInDetailExportExcelDTO.class).autoCloseStream(false).withTemplate(is).build();
            WriteSheet sheet = EasyExcel.writerSheet().build();
            Map<String, String> map = new HashMap<>();
            FillConfig build = FillConfig.builder().forceNewRow(true).build();

            SupplierDO supplierDO = supplierMapper.selectById(entryDO.getSupplier());
            if(supplierDO==null) supplierDO = new SupplierDO();
            PeopleDO peopleDO = peopleMapper.selectById(entryDO.getPeople());
            if(peopleDO==null) peopleDO = new PeopleDO();

            map.put("supplier", supplierDO.getName());
            map.put("time", entryDO.getTime().format(DateTimeFormatter.ofPattern("yyyy-MM-dd")));
            map.put("number", entryDO.getNumber());
            map.put("type", entryDO.getType()==0? "其他入库单":"盘盈单");
            map.put("total1", entryDO.getTotal().toString());
            map.put("cost", entryDO.getCost().toString());
            map.put("people", peopleDO.getName());
            map.put("logistics", JSON.parseObject(entryDO.getLogistics()).getString("number"));
            map.put("data1", entryDO.getData());

            workBook.fill(otherInDetailExportExcelList, build, sheet);
            workBook.fill(map, build, sheet);

            workBook.finish();
            try {
                is.close();
                zos.closeEntry();
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        }


        try {

            zos.finish();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

        HttpHeaders headers = new HttpHeaders();
        String filename = "OtherIn_"+ DateTime.now().toString("yyyyMMddHHmmssS") + ".zip";
        headers.setContentDispositionFormData("attachment", filename);
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        byte[] byteArray = baos.toByteArray();

        try {
            zos.close();
            baos.close();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }

        return JsonVO.success(new ResponseEntity<>(byteArray, headers, HttpStatus.OK));
    }
}
