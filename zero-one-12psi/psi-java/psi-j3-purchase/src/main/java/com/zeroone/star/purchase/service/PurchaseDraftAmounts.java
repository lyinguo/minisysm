package com.zeroone.star.purchase.service;

import com.zeroone.star.project.dto.j3.purchase.*;
import org.springframework.stereotype.Service;
import java.math.*;

/** New-draft totals are derived from lines. Legacy fraction hints only disambiguate rate representation. */
@Service
public class PurchaseDraftAmounts {
    private static BigDecimal rounded(BigDecimal value) { return value.setScale(4,RoundingMode.HALF_UP); }
    private static BigDecimal value(BigDecimal value,String field,boolean optional) {
        if(value==null && optional) return BigDecimal.ZERO.setScale(4);
        if(value==null || value.signum()<0 || value.stripTrailingZeros().scale()>4) throw new IllegalArgumentException(field+"必须为非负数且最多四位小数");
        return value.setScale(4);
    }
    private static BigDecimal rate(BigDecimal raw,String field) {
        if(raw==null) return BigDecimal.ZERO;
        if(raw.signum()<0 || raw.compareTo(new BigDecimal("100"))>0 || raw.stripTrailingZeros().scale()>2)
            throw new IllegalArgumentException(field+"须在0到100之间，最多两位小数");
        return raw;
    }
    private static BigDecimal effective(BigDecimal raw,BigDecimal base,BigDecimal hint,boolean discount) {
        if(hint!=null && raw.compareTo(BigDecimal.ONE)<=0) {
            BigDecimal percentage=rounded(base.multiply(raw).movePointLeft(2));
            BigDecimal fraction=discount ? BigDecimal.ONE.subtract(raw):raw;
            if(percentage.compareTo(hint)!=0 && rounded(base.multiply(fraction)).compareTo(hint)==0) return fraction.movePointRight(2);
        }
        return raw;
    }
    public void calculate(PurchaseNoteAddDTO request) {
        if(request==null || request.getPurchaseNoteBuyDTO()==null || request.getPurchaseNoteInfoDTOS()==null || request.getPurchaseNoteInfoDTOS().isEmpty())
            throw new IllegalArgumentException("采购单和商品明细不能为空");
        BigDecimal total=BigDecimal.ZERO,actual=BigDecimal.ZERO;
        for(PurchaseNoteInfoDTO line:request.getPurchaseNoteInfoDTOS()) {
            if(line==null) throw new IllegalArgumentException("商品明细不能为空");
            BigDecimal price=value(line.getPrice(),"单价",false),quantity=value(line.getNums(),"数量",false);
            if(quantity.signum()<=0 || price.precision()>12 || quantity.precision()>12) throw new IllegalArgumentException("数量必须大于零，单价和数量整数位不能超过8位");
            BigDecimal discount=rate(line.getDiscount(),"折扣"),tax=rate(line.getTax(),"税率");
            BigDecimal gross=rounded(price.multiply(quantity));
            BigDecimal deduction=rounded(gross.multiply(effective(discount,gross,line.getDsc(),true)).movePointLeft(2));
            BigDecimal net=gross.subtract(deduction);
            BigDecimal taxAmount=rounded(net.multiply(effective(tax,net,line.getTat(),false)).movePointLeft(2));
            BigDecimal inclusive=net.add(taxAmount);
            if(net.precision()>12 || inclusive.precision()>12) throw new IllegalArgumentException("明细金额超出允许范围");
            line.setPrice(price);line.setNums(quantity);line.setDiscount(discount);line.setTax(tax);
            line.setDsc(deduction);line.setTotal(net);line.setTat(taxAmount);line.setTpt(inclusive);
            total=total.add(net);actual=actual.add(inclusive);
        }
        if(total.precision()>16 || actual.precision()>16) throw new IllegalArgumentException("采购单总金额超出允许范围");
        PurchaseNoteBuyDTO header=request.getPurchaseNoteBuyDTO();
        header.setTotal(total);header.setActual(actual);
        header.setMoney(value(header.getMoney(),"实付金额",true));
        header.setCost(value(header.getCost(),"单据费用",true));
    }
}
