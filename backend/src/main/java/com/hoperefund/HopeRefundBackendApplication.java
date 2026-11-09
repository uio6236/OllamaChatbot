package com.hoperefund;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 희망환급 Spring Boot 애플리케이션 시작 클래스
 * 서버 실행 및 자동 설정을 담당한다.
 */
@SpringBootApplication
public class HopeRefundBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(HopeRefundBackendApplication.class, args);
    }
}
