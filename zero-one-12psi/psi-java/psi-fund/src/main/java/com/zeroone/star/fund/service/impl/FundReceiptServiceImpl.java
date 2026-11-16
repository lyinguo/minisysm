package com.zeroone.star.fund.service.impl;

import com.zeroone.star.fund.service.*;
import com.zeroone.star.project.dto.j4.fund.*;
import com.zeroone.star.project.vo.fund.ImportResultVO;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import java.util.Collections;

/** Compatibility entry points must not bypass reviewed drafts or real settlement. */
@Service
public class FundReceiptServiceImpl implements FundReceiptService {
    private final ReceiptDraftService drafts;
    private final ReceiptExportService exports;
    public FundReceiptServiceImpl(ReceiptDraftService drafts,ReceiptExportService exports){this.drafts=drafts;this.exports=exports;}
    @Override public void addReceipt(ReceiptAddDTO command){drafts.createLegacy(command);}
    @Override public ImportResultVO importReceiptData(MultipartFile file){throw new IllegalArgumentException("请先通过收款导入预览核对，再携带预览版本确认导入；不能直接逐行保存");}
    @Override public byte[] exportSimpleReceiptReport(){return exports.file("simple",Collections.emptyMap());}
    @Override public byte[] exportDetailReceiptReport(){return exports.file("detail",Collections.emptyMap());}
    @Override public void updateReceipt(ReceiptUpdateDTO command){throw new IllegalArgumentException("修改收款草稿需要当前已读版本，请使用完整单据修改入口");}
    @Override public void auditReceipt(ReceiptAuditDTO command){throw new IllegalArgumentException("审核收款需要明确审核方向及已核对的销售核销方案，请使用收款入账入口");}
    @Override public void deleteReceipt(ReceiptDeleteDTO command){throw new IllegalArgumentException("删除收款草稿需要当前已读版本，请使用完整单据删除入口");}
}
