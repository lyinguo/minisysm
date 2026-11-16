package com.zeroone.star.purchase.config;

import org.springframework.boot.web.servlet.MultipartConfigFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.unit.DataSize;
import javax.servlet.MultipartConfigElement;

@Configuration
public class PurchaseMultipartConfig {
    @Bean
    public MultipartConfigElement multipartConfigElement(){
        MultipartConfigFactory factory=new MultipartConfigFactory();
        factory.setMaxFileSize(DataSize.ofBytes(5*1024*1024));
        factory.setMaxRequestSize(DataSize.ofBytes(6*1024*1024));
        return factory.createMultipartConfig();
    }
}
