package com.zeroone.star.basic_information;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

/**
 * <p>
 * 描述：程序启动入口
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
@EnableDiscoveryClient
@SpringBootApplication
@org.springframework.context.annotation.Import(com.zeroone.star.project.config.mybatis.MybatisPlusConfig.class)
@EnableFeignClients
@MapperScan("com.zeroone.star.basic_information.mapper")
public class basic_informationApplication {

    public static void main(String[] args) {
        SpringApplication.run(basic_informationApplication.class, args);
    }

}
