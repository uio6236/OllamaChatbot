package com.hoperefund.common.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 서버 상태 확인용 Controller
 * 개발 중 Spring Boot 서버의 HTTP 응답 여부를 확인한다.
 * TODO: Spring Security 적용 시 접근 허용 범위 검토
 */
@RestController
public class HealthController {

    @GetMapping("/api/health")
    public String health() {
        return "OK";
    }
}
