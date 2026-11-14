package com.zeroone.star.login.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zeroone.star.login.entity.Menu;
import com.zeroone.star.login.mapper.MenuMapper;
import com.zeroone.star.login.service.IMenuService;
import com.zeroone.star.project.vo.login.Fun;
import com.zeroone.star.project.vo.login.MenuTreeVO;
import org.springframework.stereotype.Service;

import java.util.*;

/**
 * <p>
 * 菜单 服务实现类
 * </p>
 * @author MRME39
 */
@Service
public class MenuServiceImpl extends ServiceImpl<MenuMapper, Menu> implements IMenuService {

    @Override
    public List<MenuTreeVO> listMenuByRoleName() {
        List<Menu> allMenus = baseMapper.selectAllMenu();
        if (allMenus == null || allMenus.isEmpty()) {
            return new ArrayList<>();
        }

        Map<String, Menu> menuMap = new HashMap<>();
        for (Menu menu : allMenus) {
            if (menu != null && menu.getId() != null) {
                menuMap.put(menu.getId(), menu);
            }
        }

        List<MenuTreeVO> tree = buildMenuTree(menuMap);
        if (tree.isEmpty()) {
            return new ArrayList<>();
        }
        List<MenuTreeVO> children = tree.get(0).getChildren();
        return children == null ? new ArrayList<>() : children;
    }

    /**
     * 构建菜单，导入menue最后组装成MenuTreeVO
     */
    private List<MenuTreeVO> buildMenuTree(Map<String, Menu> Menus) {
        List<MenuTreeVO> result = new ArrayList<>();
        Map<String, MenuTreeVO> temp = new HashMap<>();
        for (Map.Entry<String, Menu> menu : Menus.entrySet()) {
            temp.put(menu.getKey(), toMenuTreeVO(menu.getValue()));
        }

        for (MenuTreeVO menu : temp.values()) {
            Menu entity = Menus.get(menu.getId());
            if (entity != null && isRootNode(entity.getPid())) {
                result.add(menu);
                break;
            }
        }

        // 先挂普通子菜单，再处理附属报表菜单，避免 setChildren(null) 导致后续 NPE
        List<Map.Entry<String, MenuTreeVO>> normalChildren = new ArrayList<>();
        List<Map.Entry<String, MenuTreeVO>> reportChildren = new ArrayList<>();
        for (Map.Entry<String, MenuTreeVO> entry : temp.entrySet()) {
            Menu entity = Menus.get(entry.getKey());
            if (entity == null || isRootNode(entity.getPid())) {
                continue;
            }
            if ("true".equals(entry.getValue().getHasReport())) {
                reportChildren.add(entry);
            } else {
                normalChildren.add(entry);
            }
        }

        for (Map.Entry<String, MenuTreeVO> entry : normalChildren) {
            Menu entity = Menus.get(entry.getKey());
            MenuTreeVO parent = temp.get(entity.getPid());
            if (parent == null) {
                continue;
            }
            parent.addChild(entry.getValue());
        }

        for (Map.Entry<String, MenuTreeVO> entry : reportChildren) {
            Menu entity = Menus.get(entry.getKey());
            MenuTreeVO parent = temp.get(entity.getPid());
            if (parent == null) {
                continue;
            }
            parent.setHasReport("true");
            parent.setReportHref(entry.getValue().getHref());
            // 不把 children 置空：用户可能在同一父节点下新增普通菜单
        }

        sortMenuTree(result, Menus);
        return result;
    }

    private boolean isRootNode(String pid) {
        return "-1".equals(pid) || pid == null || pid.isEmpty() || "0".equals(pid);
    }

    public List<String> analyroot(String root) {
        List<String> result = new ArrayList<>();
        ObjectMapper objectMapper = new ObjectMapper();
        try {
            List<Fun> funs = objectMapper.readValue(root,
                    objectMapper.getTypeFactory().constructCollectionType(List.class, Fun.class));
            for (Fun fun : funs) {
                result.add(fun.getId());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    public MenuTreeVO toMenuTreeVO(Menu m) {
        String report = m.getHasReport();
        String hasReport = (report == null || "0".equals(report)) ? "false" : "true";
        return new MenuTreeVO(m.getId(), m.getName(), m.getHref(), hasReport);
    }

    private void sortMenuTree(List<MenuTreeVO> menuTree, Map<String, Menu> originalMenus) {
        if (menuTree == null || menuTree.isEmpty()) {
            return;
        }
        menuTree.sort((m1, m2) -> {
            Menu menu1 = originalMenus.get(m1.getId());
            Menu menu2 = originalMenus.get(m2.getId());
            Integer s1 = menu1 == null || menu1.getSort() == null ? 0 : menu1.getSort();
            Integer s2 = menu2 == null || menu2.getSort() == null ? 0 : menu2.getSort();
            return s1.compareTo(s2);
        });
        for (MenuTreeVO menu : menuTree) {
            if (menu.getChildren() != null && !menu.getChildren().isEmpty()) {
                sortMenuTree(menu.getChildren(), originalMenus);
            }
        }
    }
}
