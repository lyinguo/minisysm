package com.zeroone.star.basic_information.config;

import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.project.vo.ResultStatus;
import org.springframework.validation.BindException;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import javax.validation.ConstraintViolation;
import javax.validation.ConstraintViolationException;
import javax.validation.Path;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

/**
 * <p>
 * 描述：全局异常捕获处理
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
@RestControllerAdvice
public class GlobalExceptionHandler {
    /**
     * 系统通用异常处理
     * @param e 异常类型
     * @return 返回异常信息回显数据
     */
    @ExceptionHandler(value = Exception.class)
    public JsonVO<String> exceptionHandler(Exception e) {
        for (Throwable cause = e; cause != null; cause = cause.getCause()) {
            String message = cause.getMessage();
            if (message != null && message.contains("PSI_INTEGRITY:")) {
                String reason = "数据已经被单据或库存引用，不能删除；请保留历史资料";
                if (message.contains("PSI_INTEGRITY:balance:")) reason = "存在未结清余额，不能删除";
                if (message.contains("PSI_INTEGRITY:missing:")) reason = "选择的客户、供应商、商品、仓库或账户已不存在，请刷新后重新选择";
                if (message.contains("PSI_INTEGRITY:immutable:")) reason = "基础资料的内部 ID 不允许修改";
                if (message.contains("PSI_INTEGRITY:cycle:")) reason = "不能将自身或下级设置为上级";
                if (message.contains("PSI_INTEGRITY:initial:")) reason = "资金账户已有业务流水，不能修改期初余额";
                return JsonVO.create(reason, 9999, reason);
            }
        }
        if (e instanceof IllegalArgumentException) return JsonVO.create(e.getMessage(), 9999, e.getMessage());
        if (e instanceof HttpMediaTypeException) {
            return JsonVO.create(e.getMessage(), ResultStatus.CONTENT_TYPE_ERR);
        }
        return JsonVO.create(e.getMessage(), ResultStatus.SERVER_ERROR);
    }

    /**
     * requestBody参数校验异常处理
     * @param e 异常类型
     * @return 返回异常信息回显数据
     */
    @ExceptionHandler(value =
            {MethodArgumentNotValidException.class, BindException.class})
    public JsonVO<String> methodArgumentNotValidHandler(Exception e) {
        BindingResult bindingResult;
        if (e instanceof MethodArgumentNotValidException) {
            //@RequestBody参数校验
            bindingResult = ((MethodArgumentNotValidException) e).getBindingResult();
        } else {
            //@ModelAttribute参数校验
            bindingResult = ((BindException) e).getBindingResult();
        }
        FieldError fieldError = bindingResult.getFieldError();
        String data = "";
        if (fieldError != null) {
            data = "[" + fieldError.getField() + "]" + fieldError.getDefaultMessage();
        }
        return JsonVO.create(data, ResultStatus.PARAMS_INVALID);
    }

    /**
     * requestParam参数校验异常处理
     * @param e 异常类型
     * @return 返回异常信息回显数据
     */
    @ExceptionHandler(value = {
            ConstraintViolationException.class,
            MissingServletRequestParameterException.class})
    public JsonVO<String> constraintViolationHandler(Exception e) {
        String field = "";
        String msg = "";
        if (e instanceof ConstraintViolationException) {
            ConstraintViolation<?> constraint = ((ConstraintViolationException) e)
                    .getConstraintViolations().stream().findFirst().orElse(null);
            if (constraint != null) {
                List<Path.Node> pathList = StreamSupport.stream
                                (constraint.getPropertyPath().spliterator(), false)
                        .collect(Collectors.toList());
                field = pathList.get(pathList.size() - 1).getName();
                msg = constraint.getMessage();
            }
        } else {
            // 非JSR标准返回的异常，要自定义提示文本
            field = ((MissingServletRequestParameterException) e).getParameterName();
            msg = "参数值缺失";
        }
        return JsonVO.create("[" + field + "]" + msg, ResultStatus.PARAMS_INVALID);
    }
}
