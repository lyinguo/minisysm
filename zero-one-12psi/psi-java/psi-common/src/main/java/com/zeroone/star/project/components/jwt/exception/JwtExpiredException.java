package com.zeroone.star.project.components.jwt.exception;

/**
 * <p>
 * 描述：Token过期异常定义
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
public class JwtExpiredException extends RuntimeException {
    public JwtExpiredException(String message) {
        super(message);
    }
}
