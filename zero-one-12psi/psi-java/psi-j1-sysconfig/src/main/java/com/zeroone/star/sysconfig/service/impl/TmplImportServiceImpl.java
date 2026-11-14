package com.zeroone.star.sysconfig.service.impl;

import com.alibaba.cloud.commons.lang.StringUtils;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.components.fastdfs.FastDfsClientComponent;
import com.zeroone.star.project.components.fastdfs.FastDfsFileInfo;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j1.sysconfig.TemplateAddDTO;
import com.zeroone.star.project.dto.j1.sysconfig.TemplateUpdateDTO;
import com.zeroone.star.project.query.j1.sysconfig.TempImportQuery;
import com.zeroone.star.project.vo.j1.sysconfig.TempImportDownloadVO;
import com.zeroone.star.project.vo.j1.sysconfig.TempImportVO;
import com.zeroone.star.sysconfig.entity.TmplImport;
import com.zeroone.star.sysconfig.enums.TemplateStatus;
import com.zeroone.star.sysconfig.mapper.TmplImportMapper;
import com.zeroone.star.sysconfig.service.ITmplImportService;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@Transactional
public class TmplImportServiceImpl extends ServiceImpl<TmplImportMapper, TmplImport> implements ITmplImportService {

    private static final String LOCAL_PREFIX = "local:";

    @Autowired
    TmplImportMapper tmplImportMapper;
    @Autowired
    FastDfsClientComponent fastDfsClientComponent;
    @Value("${fastdfs.nginx-servers:}")
    private String fileServerUrl;
    @Value("${fastdfs.http-secret-key:}")
    private String httpSecretKey;

    @Override
    public int importTemplate(TemplateAddDTO templateAddDTO) {
        MultipartFile file = templateAddDTO.getFile();
        if (file == null || file.isEmpty()) {
            return 0;
        }
        String templateName = templateAddDTO.getTemplateName();
        if (templateName == null || templateName.trim().isEmpty()) {
            return 0;
        }

        TmplImport tmplImport = new TmplImport();
        tmplImport.setId(UUID.randomUUID().toString().replace("-", ""));
        tmplImport.setName(templateName.trim());
        tmplImport.setRemark(templateAddDTO.getRemark());
        tmplImport.setStatus(TemplateStatus.DISABLE.getValue());
        tmplImport.setCode(UUID.randomUUID().toString());
        String ext = getExt(file.getOriginalFilename());
        tmplImport.setSaveType(StringUtils.isNotBlank(templateAddDTO.getSaveType()) ? templateAddDTO.getSaveType() : ext);

        try {
            // 本地环境 FastDFS/nginx 常不可访问，模板统一落本地，保证可下载
            saveToLocal(file, tmplImport, ext);
            return tmplImportMapper.insert(tmplImport);
        } catch (Exception ex) {
            log.error("Local template save failed", ex);
            return 0;
        }
    }

    private void saveToLocal(MultipartFile file, TmplImport tmplImport, String ext) throws IOException {
        Path dir = Paths.get(System.getProperty("user.home"), ".psi-uploads", "tmpl-import");
        Files.createDirectories(dir);
        String fileName = tmplImport.getId() + (ext.isEmpty() ? "" : "." + ext);
        Path target = dir.resolve(fileName);
        Files.write(target, file.getBytes());
        tmplImport.setSavePath(LOCAL_PREFIX + target.toString());
        tmplImport.setSaveType(StringUtils.isNotBlank(tmplImport.getSaveType()) ? tmplImport.getSaveType() : "local");
    }

    @Override
    public int deleteTemplate(String id) {
        TmplImport tmplImport = tmplImportMapper.selectById(id);
        if (tmplImport == null) {
            return 0;
        }

        deleteStoredFile(tmplImport.getSavePath());
        return tmplImportMapper.deleteById(id);
    }

    @Override
    public int updateTemplate(TemplateUpdateDTO templateUpdateDTO) {
        TmplImport tmplImport = tmplImportMapper.selectById(templateUpdateDTO.getId());
        if (tmplImport == null) {
            return 0;
        }
        String name = templateUpdateDTO.getTemplateName();
        if (name != null && !name.equals("")) {
            tmplImport.setName(name);
        }
        String remark = templateUpdateDTO.getRemark();
        if (remark != null && !remark.equals("")) {
            tmplImport.setRemark(remark);
        }
        tmplImport.setStatus(templateUpdateDTO.getStatus());
        MultipartFile file = templateUpdateDTO.getFile();
        if (file != null && !file.isEmpty()) {
            deleteStoredFile(tmplImport.getSavePath());
            try {
                String ext = getExt(file.getOriginalFilename());
                saveToLocal(file, tmplImport, ext);
            } catch (Exception ex) {
                log.error("Update template file failed", ex);
                return 0;
            }
        }
        return tmplImportMapper.updateById(tmplImport);
    }

    private void deleteStoredFile(String savePath) {
        if (savePath == null) {
            return;
        }
        if (savePath.startsWith(LOCAL_PREFIX)) {
            try {
                Files.deleteIfExists(Paths.get(savePath.substring(LOCAL_PREFIX.length())));
            } catch (IOException e) {
                log.warn("Delete local template file failed: {}", savePath);
            }
            return;
        }
        try {
            String[] parts = savePath.split(",", 2);
            if (parts.length == 2) {
                FastDfsFileInfo info = FastDfsFileInfo.builder().group(parts[0]).storageId(parts[1]).build();
                fastDfsClientComponent.deleteFile(info);
            }
        } catch (Exception e) {
            log.warn("Delete FastDFS file failed: {}", savePath);
        }
    }

    private String getExt(String name) {
        if (name == null) {
            return "";
        }
        int index = name.lastIndexOf(".");
        if (index == -1) {
            return "";
        }
        return name.substring(index + 1);
    }

    @Override
    public PageDTO<TempImportVO> queryTemplateList(TempImportQuery query) {
        Page<TmplImport> mpPage = new Page<>(query.getPageIndex(), query.getPageSize());

        QueryWrapper<TmplImport> wrapper = new QueryWrapper<>();
        wrapper.like(StringUtils.isNotBlank(query.getTemplateName()), "name", query.getTemplateName());
        wrapper.eq(StringUtils.isNotBlank(query.getTemplateCode()), "code", query.getTemplateCode());
        wrapper.eq(StringUtils.isNotBlank(query.getSaveType()), "save_type", query.getSaveType());
        wrapper.eq(query.getStatus() != null, "status", query.getStatus());
        wrapper.orderByDesc("id");
        Page<TmplImport> pageResult = tmplImportMapper.selectPage(mpPage, wrapper);

        return PageDTO.create(pageResult, this::entityToVO);
    }

    private TempImportVO entityToVO(TmplImport entity) {
        TempImportVO vo = new TempImportVO();
        vo.setId(entity.getId());
        vo.setTemplateName(entity.getName());
        vo.setTemplateCode(entity.getCode());
        vo.setSaveType(entity.getSaveType());
        vo.setRemark(entity.getRemark());
        vo.setStatus(entity.getStatus());
        return vo;
    }

    @Override
    public TempImportDownloadVO getDownloadInfoById(String id) {
        TempImportDownloadVO vo = tmplImportMapper.selectDownloadInfoById(id);
        if (vo == null) {
            throw new RuntimeException("未找到模板，ID: " + id);
        }

        String savedPath = vo.getDownloadUrl();
        if (savedPath == null || savedPath.isEmpty()) {
            throw new RuntimeException("无效的文件存储路径");
        }

        if (savedPath.startsWith(LOCAL_PREFIX) || savedPath.contains(",")) {
            // 统一走本服务代理下载，避免 FastDFS 外网地址不可访问
            vo.setDownloadUrl("/import-template/file/" + id);
            return vo;
        }

        throw new RuntimeException("无效的文件存储路径: " + savedPath);
    }

    public Path resolveLocalFile(String id) {
        TmplImport tmplImport = tmplImportMapper.selectById(id);
        if (tmplImport == null || tmplImport.getSavePath() == null) {
            return null;
        }
        if (!tmplImport.getSavePath().startsWith(LOCAL_PREFIX)) {
            return null;
        }
        return Paths.get(tmplImport.getSavePath().substring(LOCAL_PREFIX.length()));
    }

    /**
     * 读取模板文件字节（支持本地与 FastDFS）
     */
    public byte[] readTemplateBytes(String id) throws Exception {
        TmplImport tmplImport = tmplImportMapper.selectById(id);
        if (tmplImport == null || tmplImport.getSavePath() == null) {
            return null;
        }
        String savePath = tmplImport.getSavePath();
        if (savePath.startsWith(LOCAL_PREFIX)) {
            Path path = Paths.get(savePath.substring(LOCAL_PREFIX.length()));
            if (!Files.exists(path)) {
                return null;
            }
            return Files.readAllBytes(path);
        }
        if (savePath.contains(",")) {
            String[] parts = savePath.split(",", 2);
            FastDfsFileInfo info = FastDfsFileInfo.builder()
                    .group(parts[0])
                    .storageId(parts[1])
                    .build();
            try {
                return fastDfsClientComponent.downloadFile(info);
            } catch (Exception e) {
                log.error("FastDFS download failed for {}: {}", id, e.getMessage());
                throw new RuntimeException("历史模板文件存储在 FastDFS，当前无法访问。请重新编辑并上传该模板后再下载。");
            }
        }
        return null;
    }

    public String resolveDownloadFileName(String id) {
        TmplImport tmplImport = tmplImportMapper.selectById(id);
        if (tmplImport == null) {
            return id;
        }
        String savePath = tmplImport.getSavePath();
        if (savePath != null && savePath.startsWith(LOCAL_PREFIX)) {
            return Paths.get(savePath.substring(LOCAL_PREFIX.length())).getFileName().toString();
        }
        String name = tmplImport.getName() == null ? "template" : tmplImport.getName();
        String ext = tmplImport.getSaveType();
        if (ext != null && !ext.isEmpty() && !ext.equals("local") && !ext.contains("/")) {
            return name + "." + ext;
        }
        if (savePath != null && savePath.contains(".")) {
            return name + savePath.substring(savePath.lastIndexOf('.'));
        }
        return name;
    }
}
