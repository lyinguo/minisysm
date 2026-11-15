package com.zeroone.star.purchase.service;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.dto.j3.purchase.*;
import org.springframework.stereotype.Service;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;
import java.util.*;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;

/** Atomic order draft creation; it neither audits nor posts stock or money. */
@Service
public class PurchaseOrderDraftService {
    private final JdbcTemplate db;
    private final PurchaseDocumentAccess access;
    private final PurchaseDraftAmounts amounts;
    private final PurchaseSupplyService supply;
    public PurchaseOrderDraftService(JdbcTemplate db,PurchaseDocumentAccess access,PurchaseDraftAmounts amounts,PurchaseSupplyService supply) {this.db=db;this.access=access;this.amounts=amounts;this.supply=supply;}
    private String id() {return UUID.randomUUID().toString().replace("-","");}
    private boolean absent(String value) {return value==null || value.trim().isEmpty() || "0".equals(value);}
    private void length(String value,int max,String label) {if(value!=null && value.length()>max)throw new IllegalArgumentException(label+"最多"+max+"个字符");}
    private void reference(String table,String id,String frame,String label,boolean optional) {
        if(optional && absent(id))return;
        if(absent(id) || db.queryForObject("SELECT COUNT(*) FROM `"+table+"` WHERE id=?",Integer.class,id)!=1)throw new IllegalArgumentException(label+"不存在，请重新选择");
        if(frame!=null) {
            String actual=db.queryForObject("SELECT frame FROM `"+table+"` WHERE id=?",String.class,id);
            if(!"0".equals(actual) && !frame.equals(actual))throw new IllegalArgumentException(label+"与制单组织不一致");
        }
    }
    private void requireUnit(String goods,String unit){
        Map<String,Object> product=db.queryForMap("SELECT unit,units FROM goods WHERE id=?",goods);
        if(!"-1".equals(String.valueOf(product.get("unit")))){
            if(!unit.equals(String.valueOf(product.get("unit"))))throw new IllegalArgumentException("商品单位不匹配");return;
        }
        try{
            JSONArray units=new JSONArray(String.valueOf(product.get("units")));
            if(units.isEmpty())throw new IllegalArgumentException("商品多单位配置为空");
            if(unit.equals(units.getJSONObject(0).getStr("source")))return;
            BigDecimal factor=BigDecimal.ONE;
            for(Object value:units){JSONObject row=new JSONObject(value);factor=factor.multiply(row.getBigDecimal("nums",BigDecimal.ZERO));if(factor.signum()<=0)throw new IllegalArgumentException("单位换算率必须大于零");if(unit.equals(row.getStr("name")))return;}
        }catch(IllegalArgumentException error){throw error;}catch(Exception error){throw new IllegalArgumentException("商品多单位配置无效");}
        throw new IllegalArgumentException("单位不存在于商品多单位配置");
    }
    @Transactional(rollbackFor=Exception.class)
    public String create(PurchaseOrderAddDTO request) {
        return createAuthorized(request,"/purchase-order/add");
    }
    @Transactional(rollbackFor=Exception.class)
    public String createImported(PurchaseOrderAddDTO request) {
        return createAuthorized(request,"/purchase-order/import-bor");
    }
    private String createAuthorized(PurchaseOrderAddDTO request,String resource) {
        UserDTO actor=access.authorize(resource);String frame=actor.getFrameId();
        reference("frame",frame,null,"所属组织",false);
        if(request==null || request.getPurchaseOrderInfoDTOList()==null || request.getPurchaseOrderInfoDTOList().isEmpty() || request.getPurchaseOrderInfoDTOList().size()>200)
            throw new IllegalArgumentException("请填写1到200条采购订单明细");
        String number=request.getNumber()==null?"":request.getNumber().trim();
        if(number.isEmpty() || number.length()>32)throw new IllegalArgumentException("采购订单编号必须为1到32个字符");
        if(request.getTime()==null || request.getArrival()==null || request.getArrival().isBefore(request.getTime()))throw new IllegalArgumentException("请填写有效单据日期，到货日期不能早于单据日期");
        reference("supplier",request.getSupplier(),frame,"供应商",false);
        reference("people",request.getPeople(),frame,"关联人员",true);
        reference("sor",request.getSource(),frame,"来源销售订单",true);
        length(request.getData(),256,"订单备注");
        PurchaseNoteBuyDTO header=new PurchaseNoteBuyDTO();header.setMoney(BigDecimal.ZERO);header.setCost(BigDecimal.ZERO);
        PurchaseNoteAddDTO calculation=new PurchaseNoteAddDTO();calculation.setPurchaseNoteBuyDTO(header);
        List<PurchaseNoteInfoDTO> lines=new ArrayList<>();
        for(PurchaseOrderInfoDTO line:request.getPurchaseOrderInfoDTOList()) {
            if(line==null)throw new IllegalArgumentException("采购订单明细不能为空");
            reference("goods",line.getGoods(),null,"商品",false);
            reference("warehouse",line.getWarehouse(),frame,"仓库",false);
            if(line.getUnit()==null || line.getUnit().trim().isEmpty())throw new IllegalArgumentException("商品单位不能为空");
            requireUnit(line.getGoods(),line.getUnit());
            length(line.getUnit(),32,"商品单位");length(line.getAttr(),64,"辅助属性");length(line.getData(),256,"明细备注");
            if(!absent(line.getAttr()) && db.queryForObject("SELECT COUNT(*) FROM attr WHERE pid=? AND name=?",Integer.class,line.getGoods(),line.getAttr())!=1)
                throw new IllegalArgumentException("商品辅助属性不存在，请重新选择");
            PurchaseNoteInfoDTO item=new PurchaseNoteInfoDTO();item.setGoods(line.getGoods());item.setPrice(line.getPrice());item.setNums(line.getNums());
            item.setDiscount(line.getDiscount());item.setTax(line.getTax());
            // Order rates use percentage points. Untrusted amounts never become legacy rate hints.
            lines.add(item);
        }
        calculation.setPurchaseNoteInfoDTOS(lines);amounts.calculate(calculation);
        db.update("INSERT INTO psi_document_write_lock(scope) VALUES('bor') ON DUPLICATE KEY UPDATE scope='bor'");
        db.queryForObject("SELECT scope FROM psi_document_write_lock WHERE scope='bor' FOR UPDATE",String.class);
        if(!db.queryForList("SELECT id FROM bor WHERE number=? FOR UPDATE",number).isEmpty())throw new IllegalArgumentException("采购订单编号已被使用");
        for(PurchaseOrderInfoDTO line:request.getPurchaseOrderInfoDTOList()) supply.require(frame,line.getGoods(),request.getSupplier());
        String order=id();
        db.update("INSERT INTO bor(id,source,frame,supplier,time,number,total,actual,people,arrival,logistics,file,data,more,examine,state,`user`) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'{}',0,0,?)",
            order,absent(request.getSource())?"0":request.getSource(),frame,request.getSupplier(),request.getTime().atStartOfDay(),number,header.getTotal(),header.getActual(),
            absent(request.getPeople())?null:request.getPeople(),request.getArrival().atStartOfDay(),request.getLogistics(),request.getFile()==null?"":request.getFile(),request.getData(),actor.getId());
        for(int i=0;i<lines.size();i++) {
            PurchaseOrderInfoDTO original=request.getPurchaseOrderInfoDTOList().get(i);PurchaseNoteInfoDTO line=lines.get(i);
            db.update("INSERT INTO bor_info(id,pid,goods,attr,unit,warehouse,price,nums,discount,dsc,total,tax,tat,tpt,data,handle) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                id(),order,original.getGoods(),original.getAttr(),original.getUnit(),original.getWarehouse(),line.getPrice(),line.getNums(),line.getDiscount(),line.getDsc(),line.getTotal(),line.getTax(),line.getTat(),line.getTpt(),original.getData());
        }
        db.update("INSERT INTO record(id,type,source,time,`user`,info) VALUES(?,'bor',?,NOW(),?,?)",id(),order,actor.getId(),"新增采购订单 "+number);
        db.update("INSERT INTO log(id,time,`user`,info) VALUES(?,NOW(),?,?)",id(),actor.getId(),"新增采购订单，单号："+number);
        return order;
    }
}
