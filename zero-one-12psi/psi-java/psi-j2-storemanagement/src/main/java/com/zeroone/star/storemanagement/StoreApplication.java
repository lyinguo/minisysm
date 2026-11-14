package com.zeroone.star.storemanagement;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.annotation.Import;
import com.zeroone.star.project.config.redis.RedisConfig;

/**
 * <p>
 * 描述：程序启动入口
 * </p>
 * @author 阿伟学长
 * @version 1.0.0
 */
@EnableDiscoveryClient
@SpringBootApplication
@Import(RedisConfig.class)
@EnableFeignClients
@MapperScan("com.zeroone.star.storemanagement.mapper")
public class StoreApplication {

    public static void main(String[] args) {
        SpringApplication.run(StoreApplication.class, args);
    }

}
