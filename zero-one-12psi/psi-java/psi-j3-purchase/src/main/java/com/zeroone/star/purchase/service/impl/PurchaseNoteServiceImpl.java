package com.zeroone.star.purchase.service.impl;

import cn.hutool.core.lang.UUID;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.dto.j3.purchase.*;
import com.zeroone.star.purchase.DO.*;
import com.zeroone.star.purchase.mapper.*;
import com.zeroone.star.purchase.service.PurchaseNoteService;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.stream.Collectors;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.zeroone.star.project.dto.j3.purchase.PurchaseNoteBuildDTO;
import com.zeroone.star.project.dto.j3.purchase.PurchaseNoteBorDTO;
import com.zeroone.star.project.dto.j3.purchase.PurchaseNoteBuilInfoDTO;
import com.zeroone.star.project.dto.j3.purchase.GoodsDataDTO;
import com.zeroone.star.project.dto.j3.purchase.WarehouseDataDTO;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;

@Service
@Slf4j
public class PurchaseNoteServiceImpl implements PurchaseNoteService {

    @Autowired
    private BuyMapper buyMapper;

    @Autowired
    private BuyInfoMapper buyInfoMapper;

    @Autowired
    private RecordMapper recordMapper;

    @Autowired
    private LogMapper logMapper;

    @Autowired
    private GoodsMapper goodsMapper;

    @Autowired
    private WarehouseMapper warehouseMapper;

    @Resource
    private UserHolder userHolder;


    @Autowired
    private UserMapper userMapper;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseDraftValidation draftValidation;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseDeleteService purchaseDelete;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseDraftAmounts purchaseAmounts;
    @Resource
    private com.zeroone.star.purchase.service.PurchaseDocumentAccess purchaseAccess;

    /**
     * 新增采购单
     * @param purchaseNoteAddDTO 采购单数据
     * @return 是否成功
     * @author TWTW
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public String addPurchaseNote(PurchaseNoteAddDTO purchaseNoteAddDTO) {
        purchaseAccess.authorize("/purchase-note/add");
        purchaseAmounts.calculate(purchaseNoteAddDTO);
        draftValidation.validate(purchaseNoteAddDTO);
        //合并 合并
        try {
            // 1. 转换并保存采购单主表数据
            BuyDO buyDO = convertToBuyDO(purchaseNoteAddDTO.getPurchaseNoteBuyDTO());
            int buyResult = buyMapper.insert(buyDO);
            if (buyResult <= 0) {
                throw new RuntimeException("保存采购单主表失败");
            }

            // 2. 转换并保存采购单明细数据
            List<BuyInfoDO> buyInfoDOList = convertToBuyInfoDOList(
                    purchaseNoteAddDTO.getPurchaseNoteInfoDTOS(),
                    buyDO.getId(), // 使用数据库自增返回的ID
                    buyDO.getSource()
            );

            for (BuyInfoDO buyInfoDO : buyInfoDOList) {
                int infoResult = buyInfoMapper.insert(buyInfoDO);
                if (infoResult <= 0) {
                    throw new RuntimeException("保存采购单明细失败");
                }
            }

            // 3. 插入操作记录到 record 表
            insertRecord(buyDO);

            // 4. 插入操作日志到 log 表
            insertLog(buyDO);

            log.info("采购单新增成功，单号：{}，主表ID：{}", buyDO.getNumber(), buyDO.getId());
            return buyDO.getId();

        } catch (Exception e) {
            log.error("采购单新增失败：{}", e.getMessage(), e);
            throw new RuntimeException("采购单新增失败：" + e.getMessage());
        }
    }

    /**
     * 转换采购单主表DTO为DO
     * @param buyDTO 采购单主表DTO
     * @return 采购单主表DO
     * @author TWTW
     */
    private BuyDO convertToBuyDO(PurchaseNoteBuyDTO buyDTO) {
        BuyDO buyDO = new BuyDO();

        try {
            // 1. 获取当前用户ID（从userHolder获取）
            UserDTO currentUser = userHolder.getCurrentUser();
            String userId = String.valueOf(currentUser.getId()); // 确保ID是String类型（匹配UserDO的id字段）

            // 2. 根据userId查询UserDO，获取frame信息
            UserDO userDO = userMapper.selectById(userId);
            if (userDO == null) {
                throw new RuntimeException("用户不存在，userId: " + userId); // 明确异常信息
            }

            // 3. 设置frame和userId到buyDO
            buyDO.setFrame(userDO.getFrame()); // 从数据库查询的UserDO中获取frame
            buyDO.setUser(userId);

        } catch (RuntimeException e) {
            // 保留原有运行时异常抛出（或根据业务调整异常类型）
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("获取用户组织信息失败", e); // 增强异常提示
        }

        // 字段映射
        buyDO.setSource(buyDTO.getSource() == null ? "0" : buyDTO.getSource());
//        buyDO.setFrame(String.valueOf(buyDTO.getFrame())); // 用户ID 通过负载信息获取
        buyDO.setSupplier(String.valueOf(buyDTO.getSupplier()));
        buyDO.setTime(convertDateStringToLocalDateTime(buyDTO.getTime()));
        buyDO.setNumber(buyDTO.getNumber());
        buyDO.setTotal(buyDTO.getTotal());
        buyDO.setActual(buyDTO.getActual());
        buyDO.setMoney(buyDTO.getMoney());
        buyDO.setCost(buyDTO.getCost());
        buyDO.setAccount(buyDTO.getAccount() != null ? String.valueOf(buyDTO.getAccount()) : null);
        buyDO.setPeople(buyDTO.getPeople() != null ? String.valueOf(buyDTO.getPeople()) : null);
        buyDO.setLogistics(buyDTO.getLogistics());
        buyDO.setFile(buyDTO.getFile() == null ? "" : buyDTO.getFile());
        buyDO.setData(buyDTO.getData());
        buyDO.setExamine(0);
        buyDO.setNucleus(0);
        buyDO.setCse(buyDTO.getCost() != null && buyDTO.getCost().signum() > 0 ? 0 : 3);
        buyDO.setInvoice(0);
        buyDO.setCheck(false);
//        buyDO.setUser("System");
        // 用户ID 通过负载信息获取

        return buyDO;
    }

    /**
     * 转换采购单明细DTO列表为DO列表
     * @param infoDTOList 采购单明细DTO列表
     *                    采购单ID
     *                    采购单来源
     * @return 采购单明细DO列表
     * @author TWTW
     */
    private List<BuyInfoDO> convertToBuyInfoDOList(List<PurchaseNoteInfoDTO> infoDTOList, String pid, String source) {
        List<BuyInfoDO> buyInfoDOList = new ArrayList<>();

        for (PurchaseNoteInfoDTO infoDTO : infoDTOList) {
            BuyInfoDO buyInfoDO = new BuyInfoDO();

            // 注意：不设置ID，让数据库自增生成
            buyInfoDO.setPid(pid); // 使用主表返回的ID作为外键

            // 字段映射
            buyInfoDO.setSource(infoDTO.getSource());
            buyInfoDO.setGoods(String.valueOf(infoDTO.getGoods()));
            buyInfoDO.setAttr(infoDTO.getAttr());
            buyInfoDO.setUnit(infoDTO.getUnit());
            buyInfoDO.setWarehouse(infoDTO.getWarehouse());
            buyInfoDO.setBatch(infoDTO.getBatch());
            buyInfoDO.setMfd(infoDTO.getMfd() == null || infoDTO.getMfd().trim().isEmpty() ? null : LocalDate.from(convertDateStringToLocalDateTime(infoDTO.getMfd())));
            buyInfoDO.setSerial(infoDTO.getSerial());
            buyInfoDO.setPrice(infoDTO.getPrice());
            buyInfoDO.setNums(infoDTO.getNums());
            buyInfoDO.setDiscount(infoDTO.getDiscount());
            buyInfoDO.setDsc(infoDTO.getDsc());
            buyInfoDO.setTotal(infoDTO.getTotal());
            buyInfoDO.setTax(infoDTO.getTax());
            buyInfoDO.setTat(infoDTO.getTat());
            buyInfoDO.setTpt(infoDTO.getTpt());
            buyInfoDO.setData(infoDTO.getData());
            buyInfoDO.setRetreat(BigDecimal.ZERO); // 默认退货数量为0

            buyInfoDOList.add(buyInfoDO);
        }

        return buyInfoDOList;
    }

    /**
     * 将日期字符串（如"2025-10-30"或"2025-10-30 12:34:56"）转换为LocalDateTime
     * 支持格式：yyyy-MM-dd、yyyy-MM-dd HH:mm:ss、yyyy-MM-dd'T'HH:mm:ss
     * @param dateStr 日期字符串
     *                默认处理为yyyy-MM-dd HH:mm:ss
     * @return LocalDateTime
     * @author TWTW
     */
    private LocalDateTime convertDateStringToLocalDateTime(String dateStr) {
        // 处理空字符串或null，返回当前时间
        if (dateStr == null || dateStr.trim().isEmpty()) {
            throw new IllegalArgumentException("单据日期不能为空");
        }

        // 定义支持的日期格式（可根据实际需求扩展）
        DateTimeFormatter[] formatters = {
                DateTimeFormatter.ISO_LOCAL_DATE_TIME, // 支持 yyyy-MM-dd'T'HH:mm:ss
                DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
                DateTimeFormatter.ISO_LOCAL_DATE // 支持 yyyy-MM-dd（转换为当天0点）
        };

        // 尝试用每种格式解析
        for (DateTimeFormatter formatter : formatters) {
            try {
                if (formatter == DateTimeFormatter.ISO_LOCAL_DATE) {
                    // 纯日期字符串转换为当天0点的LocalDateTime
                    return LocalDate.parse(dateStr, formatter).atStartOfDay();
                } else {
                    return LocalDateTime.parse(dateStr, formatter);
                }
            } catch (DateTimeParseException e) {
                // 解析失败则尝试下一种格式，不处理异常
            }
        }

        // 所有格式都解析失败时，返回当前时间
        throw new IllegalArgumentException("日期格式无效，请使用yyyy-MM-dd或完整日期时间");
    }

    /**
     * 插入操作记录到 record 表
     * @param buyDO 采购单DO
     * @author TWTW
     */
    private void insertRecord(BuyDO buyDO) {
        RecordDO recordDO = new RecordDO();

        // 生成32位ID
        recordDO.setId(generate32Id());

        // 设置记录信息
        recordDO.setType("buy"); // 单据类型为采购单
        recordDO.setSource(String.valueOf(buyDO.getId())); // 关联单据为采购单ID
        recordDO.setTime(buyDO.getTime()); // 使用采购单时间
        recordDO.setUser(String.valueOf(buyDO.getUser())); // 制单人
        recordDO.setInfo("新增单据"); // 操作内容

        int recordResult = recordMapper.insert(recordDO);
        if (recordResult <= 0) {
            throw new RuntimeException("保存操作记录失败");
        }
    }

    /**
     * 插入操作日志到 log 表
     * @param buyDO 采购单DO
     * @author TWTW
     */
    private void insertLog(BuyDO buyDO) {
        LogDO logDO = new LogDO();

        // 生成32位ID
        logDO.setId(generate32Id());

        // 设置日志信息
        logDO.setTime(LocalDateTime.now()); // 操作时间为当前时间
        logDO.setUser(String.valueOf(buyDO.getUser())); // 所属用户
        logDO.setInfo("新增采购单，单号：" + buyDO.getNumber()); // 操作内容

        int logResult = logMapper.insert(logDO);
        if (logResult <= 0) {
            throw new RuntimeException("保存操作日志失败");
        }
    }
    /**
     * 生成32位ID
     * @return 32位ID
     * @author TWTW
     */
    private String generate32Id() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 32);
    }

    /**
     * 删除采购单（支持批量）
     * @param ids 采购单ID列表
     * @return 删除结果
     * @author TWTW
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public String deletePurchase(List<String> ids) {
        return "成功删除 "+purchaseDelete.delete(ids)+" 张采购草稿";
    }

    /**
     * 获取生成采购退货单数据
     * @param id 采购单ID
     * @return 采购退货单数据
     * @author TWTW
     */
    @Override
    public PurchaseNoteBuildDTO getBuildBreData(String id) {
        if (StringUtils.isBlank(id)) {
            throw new RuntimeException("采购单ID不能为空");
        }

        try {
            // 1. 查询采购单主表信息
            BuyDO buyDO = buyMapper.selectById(id);
            if (buyDO == null) {
                throw new RuntimeException("采购单不存在，ID：" + id);
            }

            // 2. 构建采购单核心信息
            PurchaseNoteBorDTO borDTO = buildPurchaseNoteBorDTO(buyDO);

            // 3. 查询采购单明细并构建返回数据
            List<PurchaseNoteBuilInfoDTO> builInfoDTOList = buildPurchaseNoteBuilInfoDTOList(id);

            // 4. 构建返回结果
            PurchaseNoteBuildDTO buildDTO = new PurchaseNoteBuildDTO();
            buildDTO.setPurchaseNoteBorDTO(borDTO);
            buildDTO.setPurchaseNoteBuilInfoDTOS(builInfoDTOList);

            return buildDTO;

        } catch (Exception e) {
            log.error("获取生成采购退货单数据失败：{}", e.getMessage(), e);
            throw new RuntimeException("获取生成采购退货单数据失败：" + e.getMessage());
        }
    }

    /**
     * 构建采购单核心信息
     * @param buyDO 采购单DO对象
     * @author TWTW
     */
    private PurchaseNoteBorDTO buildPurchaseNoteBorDTO(BuyDO buyDO) {
        PurchaseNoteBorDTO borDTO = new PurchaseNoteBorDTO();

        // 设置关联上游单据ID（采购单ID）
        borDTO.setSource(buyDO.getId());

        // 设置供应商ID
        borDTO.setSupplier(buyDO.getSupplier());

        // 设置采购单总金额
        borDTO.setTotal(buyDO.getTotal());

        return borDTO;
    }

    /**
     * 构建采购单明细列表
     * @param pid 采购单ID
     * @author TWTW
     */
    private List<PurchaseNoteBuilInfoDTO> buildPurchaseNoteBuilInfoDTOList(String pid) {
        // 查询采购单明细
        QueryWrapper<BuyInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("pid", pid);
        List<BuyInfoDO> buyInfoList = buyInfoMapper.selectList(queryWrapper);

        if (buyInfoList.isEmpty()) {
            throw new RuntimeException("采购单明细不存在，采购单ID：" + pid);
        }

        List<PurchaseNoteBuilInfoDTO> resultList = new ArrayList<>();

        for (BuyInfoDO buyInfo : buyInfoList) {
            PurchaseNoteBuilInfoDTO builInfoDTO = new PurchaseNoteBuilInfoDTO();

            // 设置基本信息
            builInfoDTO.setId(buyInfo.getId());
            builInfoDTO.setPid(buyInfo.getPid());
            builInfoDTO.setSource(buyInfo.getSource());
            builInfoDTO.setGoods(buyInfo.getGoods());
            builInfoDTO.setAttr(buyInfo.getAttr());
            builInfoDTO.setUnit(buyInfo.getUnit());
            builInfoDTO.setWarehouse(buyInfo.getWarehouse());
            builInfoDTO.setBatch(buyInfo.getBatch());

            // 转换生产日期格式
            if (buyInfo.getMfd() != null) {
                builInfoDTO.setMfd(buyInfo.getMfd().toString());
            }

            builInfoDTO.setPrice(buyInfo.getPrice());
            builInfoDTO.setNums(buyInfo.getNums());
            builInfoDTO.setSerial(buyInfo.getSerial());
            builInfoDTO.setDiscount(buyInfo.getDiscount());
            builInfoDTO.setDsc(buyInfo.getDsc());
            builInfoDTO.setTotal(buyInfo.getTotal());
            builInfoDTO.setTax(buyInfo.getTax());
            builInfoDTO.setTat(buyInfo.getTat());
            builInfoDTO.setTpt(buyInfo.getTpt());
            builInfoDTO.setData(buyInfo.getData());
            builInfoDTO.setRetreat(buyInfo.getRetreat());

            // 查询并设置商品信息
            GoodsDataDTO goodsData = getGoodsData(buyInfo.getGoods());
            builInfoDTO.setGoodsData(goodsData);

            // 查询并设置仓库信息
            WarehouseDataDTO warehouseData = getWarehouseData(buyInfo.getWarehouse());
            builInfoDTO.setWarehouseData(warehouseData);

            resultList.add(builInfoDTO);
        }

        return resultList;
    }

    /**
     * 获取商品信息
     * @param goodsId 商品ID
     * @author TWTW
     */
    private GoodsDataDTO getGoodsData(String goodsId) {
        GoodsDO goodsDO = goodsMapper.selectById(goodsId);
        if (goodsDO == null) {
            return null;
        }

        GoodsDataDTO goodsData = new GoodsDataDTO();
        goodsData.setId(goodsDO.getId());
        goodsData.setName(goodsDO.getName());
        goodsData.setPy(goodsDO.getPy());
        goodsData.setNumber(goodsDO.getNumber());
        goodsData.setSpec(goodsDO.getSpec());
        goodsData.setCategory(goodsDO.getCategory());
        goodsData.setBrand(goodsDO.getBrand());
        goodsData.setUnit(goodsDO.getUnit());
        goodsData.setBuy(goodsDO.getBuy());
        goodsData.setSell(goodsDO.getSell());
        goodsData.setCode(goodsDO.getCode());
        goodsData.setLocation(goodsDO.getLocation());
        goodsData.setStock(goodsDO.getStock());
        goodsData.setType(goodsDO.getType());
        goodsData.setData(goodsDO.getData());
        goodsData.setImgs(goodsDO.getImgs());
        goodsData.setDetails(goodsDO.getDetails());
        goodsData.setUnits(goodsDO.getUnits());
        goodsData.setStrategy(goodsDO.getStrategy());
        goodsData.setSerial(goodsDO.getSerial() == 1);
        goodsData.setBatch(goodsDO.getBatch() == 1);
        goodsData.setValidity(goodsDO.getValidity() == 1);
        goodsData.setProtect(goodsDO.getProtect());
        goodsData.setThreshold(goodsDO.getThreshold());
        goodsData.setMore(goodsDO.getMore());

        return goodsData;
    }

    /**
     * 获取仓库信息
     * @param warehouseId 仓库ID
     * @author TWTW
     */
    private WarehouseDataDTO getWarehouseData(String warehouseId) {
        QueryWrapper<WarehouseDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.select("id", "name", "number", "frame", "contacts", "tel", "`add`", "data")
                .eq("id", warehouseId);

        WarehouseDO warehouseDO = warehouseMapper.selectOne(queryWrapper);
        if (warehouseDO == null) {
            return null;
        }

        WarehouseDataDTO warehouseData = new WarehouseDataDTO();
        try {
            warehouseData.setId(warehouseDO.getId());
            warehouseData.setName(warehouseDO.getName());
            warehouseData.setNumber(warehouseDO.getNumber());
            warehouseData.setFrame(warehouseDO.getFrame());
            warehouseData.setContacts(warehouseDO.getContacts());
            warehouseData.setTel(warehouseDO.getTel());
            warehouseData.setAdd(warehouseDO.getAdd());
            warehouseData.setData(warehouseDO.getData());
        } catch (NumberFormatException e) {
            log.warn("仓库ID格式转换失败：{}", warehouseId);
            return null;
        }

        return warehouseData;
    }
}
