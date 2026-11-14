package com.zeroone.star.project.utils.tree;

/**
 * <p>
 * 描述：对象转换节点数据匹配接口
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
public interface TreeNodeMapper<T> {

    /**
     * 把一个对象转换为节点的数据对象
     * @param object 被转换对象
     * @return 转换后的节点数据
     */
    TreeNode objectMapper(T object);
}
