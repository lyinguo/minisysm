package com.zeroone.star.basic_information.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.basic_information.entity.Frame;
import com.zeroone.star.basic_information.mapper.FrameMapper;
import com.zeroone.star.basic_information.service.IFrameService;
import com.zeroone.star.project.dto.j6.basic_information.frame.FrameDTO;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;
@Service
public class FrameServiceImpl extends ServiceImpl<FrameMapper, Frame> implements IFrameService {
    @Resource
    MsFrameMapper ms;
    /**
     * 获取完整的组织结构树
     */
    public List<FrameDTO> getFrame() {
        // 从数据库查询所有 DO
        List<Frame> allFrame = baseMapper.selectList(null);

        // 转换为 DTO
        List<FrameDTO> allDTOs = ms.framesToFrameDtos(allFrame);

        // Root organizations historically use NULL, an empty string or "0".
        // Build from every persisted node without letting old cycles crash callers.
        java.util.Set<String> ids = allDTOs.stream().map(FrameDTO::getId).collect(Collectors.toSet());
        allDTOs.sort(Comparator.comparing(FrameDTO::getSort, Comparator.nullsLast(Comparator.naturalOrder()))
                .thenComparing(FrameDTO::getId));
        java.util.Set<String> visited = new java.util.HashSet<>();
        List<FrameDTO> roots = new java.util.ArrayList<>();
        for (FrameDTO node : allDTOs) {
            String parent = node.getPid();
            if (parent == null || parent.trim().isEmpty() || "0".equals(parent) || !ids.contains(parent)) {
                FrameDTO root = attach(node, allDTOs, visited);
                if (root != null) roots.add(root);
            }
        }
        for (FrameDTO node : allDTOs) {
            FrameDTO remainder = attach(node, allDTOs, visited);
            if (remainder != null) roots.add(remainder);
        }
        return roots;
    }

    private FrameDTO attach(FrameDTO node, List<FrameDTO> all, java.util.Set<String> visited) {
        if (!visited.add(node.getId())) return null;
        List<FrameDTO> children = new java.util.ArrayList<>();
        for (FrameDTO candidate : all) {
            if (Objects.equals(candidate.getPid(), node.getId())) {
                FrameDTO child = attach(candidate, all, visited);
                if (child != null) children.add(child);
            }
        }
        node.setChildren(children);
        node.setHasChildren(!children.isEmpty());
        return node;
    }
}
