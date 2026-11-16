package com.zeroone.star.fund.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.fund.entity.ImyInfo;
import com.zeroone.star.fund.mapper.ImyInfoMapper;
import com.zeroone.star.fund.mapper.ImyMapper;
import com.zeroone.star.fund.service.FundReceiptFormService;
import com.zeroone.star.fund.util.mapstruct.ReceiptMapper;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j4.fund.FundReceiptDetailDTO;
import com.zeroone.star.project.dto.j4.fund.FundReceiptListDTO;
import com.zeroone.star.project.query.j4.fund.FundReceiptListQuery;
import com.zeroone.star.project.vo.JsonVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class FundReceiptFormServiceImpl implements FundReceiptFormService {
    @Autowired
    private ImyInfoMapper imyInfoMapper;

    @Autowired
    private ImyMapper imyMapper;
    @Autowired
    private com.zeroone.star.fund.service.ReceiptDocumentAccess access;
    @Autowired
    private org.springframework.jdbc.core.JdbcTemplate db;

    @Override
    @org.springframework.transaction.annotation.Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
    public JsonVO<FundReceiptDetailDTO> selectFundReceiptDetail(String id) {
        com.zeroone.star.project.components.user.UserDTO actor=access.authorize("/fund/receipt/fundReceiptDetail");
        java.util.List<String> frames=db.queryForList("SELECT frame FROM imy WHERE id=?",String.class,id);
        if(frames.size()!=1)throw new IllegalArgumentException("收款单不存在");
        access.requireFrame(actor,frames.get(0));
        LambdaQueryWrapper<ImyInfo> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(ImyInfo::getPid, id);
        java.util.List<ImyInfo> details=imyInfoMapper.selectList(queryWrapper);
        if(details.size()>1)throw new IllegalArgumentException("本单有多条账户明细，请通过完整收款单详情查看，不能只返回一条明细");
        ImyInfo imyInfo = details.isEmpty()?null:details.get(0);
        FundReceiptDetailDTO dto = ReceiptMapper.INSTANCE.toDTO(imyInfo);
        if (dto == null) {
            return JsonVO.fail(dto);
        }
        return JsonVO.success(dto);
    }



    @Override
    @org.springframework.transaction.annotation.Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
    public JsonVO<PageDTO<FundReceiptListDTO>> pageList(FundReceiptListQuery query) {
        com.zeroone.star.project.components.user.UserDTO actor=access.authorize("/fund/receipt/fundReceiptList");
        if(query==null)throw new IllegalArgumentException("请提交查询条件");
        if(query.getExamine()!=null && (query.getExamine()<0 || query.getExamine()>1))throw new IllegalArgumentException("审核状态无效");
        if(query.getNucleus()!=null && (query.getNucleus()<0 || query.getNucleus()>2))throw new IllegalArgumentException("核销状态无效");
        if(query.getBeginTime()!=null && query.getEndTime()!=null && query.getBeginTime().isAfter(query.getEndTime()))throw new IllegalArgumentException("查询开始日期不能晚于结束日期");
        long current=query.getPageIndex()<1?1:Math.min(query.getPageIndex(),1000000L);
        long size=query.getPageSize()<1?10:Math.min(query.getPageSize(),100L);
        IPage<FundReceiptListDTO> page = new Page<>(current,size);
        IPage<FundReceiptListDTO> resultPage = imyMapper.listAll(page, query,actor.getRoles().contains("ROLE_ADMIN")?null:actor.getFrameId());
        // 转换为PageDTO（根据实际结构调整）
        PageDTO<FundReceiptListDTO> res = new PageDTO<>(
                  resultPage.getCurrent(),
                resultPage.getSize(),
                resultPage.getTotal(),
                resultPage.getPages(),
                resultPage.getRecords()
        );

        return JsonVO.success(res);
    }
}
