package com.zeroone.star.storemanagement.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j2.store.OtherInListAddDTO;
import com.zeroone.star.project.dto.j2.store.OtherInListDTO;
import com.zeroone.star.project.dto.j2.store.OtherInListDetailDTO;
import com.zeroone.star.project.query.j2.store.OtherInQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.storemanagement.entity.EntryDO;
import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

public interface IOtherInService extends IService<EntryDO> {
    void updateOtherInList(OtherInListDetailDTO otherInListDetailDTO);




    JsonVO<String> saveOtherInList(OtherInListAddDTO dto);



    OtherInListAddDTO previewOtherInList(OtherInListAddDTO dto);
}
