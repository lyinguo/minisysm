package com.zeroone.star.project.components.jwt.exception;

/**
 * <p>
 * 描述：Token无效异常定义
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
public class JwtInvalidException extends RuntimeException {
    public JwtInvalidException(String message) {
        super(message);
    }
}
