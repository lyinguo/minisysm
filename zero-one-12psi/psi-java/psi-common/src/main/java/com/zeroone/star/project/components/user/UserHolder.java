package com.zeroone.star.project.components.user;

import cn.hutool.core.convert.Convert;
import cn.hutool.json.JSONObject;
import com.zeroone.star.project.components.jwt.JwtComponent;
import com.zeroone.star.project.components.jwt.exception.JwtInvalidException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;

/**
 * <p>
 * 描述：获取登录用户信息
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
@Component
@Slf4j
public class UserHolder {
    @Resource
    JwtComponent jwtComponent;

    /**
     * 从请求头中获取用户信息
     * @return 用户信息
     * @throws Exception 解析失败抛出异常
     */
    @SuppressWarnings("MismatchedQueryAndUpdateOfCollection")
    public UserDTO getCurrentUser() throws Exception {
        // 从Header中获取用户信息
        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (servletRequestAttributes == null) {
            return null;
        }
        HttpServletRequest request = servletRequestAttributes.getRequest();
        // A caller can forge a `user` header, including a privileged identity.
        // Derive identity only from a signed, unexpired bearer credential.
        String authorization = request.getHeader("Authorization");
        if (authorization == null || !authorization.regionMatches(true, 0, "Bearer ", 0, 7)
                || authorization.substring(7).trim().isEmpty()) throw new JwtInvalidException("请先登录");
        String userStr = jwtComponent.defaultRsaVerify(authorization.substring(7).trim());
        JSONObject userJsonObject = new JSONObject(userStr);

        // FIXME: 如果要扩展用户信息，需要修改这里的代码
        return UserDTO.builder()
                .id(Convert.toStr(userJsonObject.get("id")))
                .username(userJsonObject.getStr("user_name"))
                //.isEnabled(Convert.toByte(1))
                .avatar(Convert.toStr(userJsonObject.get("avatar")))
                .roles(Convert.toList(String.class, userJsonObject.get("authorities")))
                .frameId(Convert.toStr(userJsonObject.get("frameId")))
                .frameName(Convert.toStr(userJsonObject.get("frameName")))
                .build();
    }

    /**
     * 从请求头中获取当前请求的token
     * @return 没有获取到返回null
     */
    public String getCurrentToken() {
        ServletRequestAttributes servletRequestAttributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (servletRequestAttributes == null) {
            return null;
        }
        HttpServletRequest request = servletRequestAttributes.getRequest();
        String token = request.getHeader("Authorization");
        if (StringUtils.isEmpty(token)) {
            return null;
        }
        return token.replace("Bearer ", "");
    }
}
