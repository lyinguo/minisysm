package com.zeroone.star.purchase.service.impl;
import com.zeroone.star.purchase.service.IPurchaseOrderReportService;
import com.zeroone.star.purchase.service.PurchaseOrderExportService;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.List;
@Service
public class PurchaseOrderReportServiceImpl implements IPurchaseOrderReportService {
    @Resource private PurchaseOrderExportService exports;
    @Override public byte[] exportPurchaseOrderReport(List<String> ids){return exports.detailed(ids);}
}
