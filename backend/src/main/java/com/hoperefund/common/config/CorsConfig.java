package com.hoperefund.common.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * React 프론트엔드와 Spring Boot 간 CORS 설정
 * 개발 환경의 React 서버에서 API 요청을 허용한다.
 * TODO: Spring Security 연동 시 CORS 정책 통합 검토
 * TODO: 배포 시 운영 도메인으로 허용 출처 변경
 */
@Configuration // Spring Boot 설정 클래스 등록
public class CorsConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {

        registry.addMapping("/api/**") // /api/로 시작하는 API에 적용
                .allowedOrigins("http://localhost:5173") // 요청을 허용할 React 주소
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS") // 허용할 HTTP 요청 방식
                .allowedHeaders(
                        "Content-Type", "Authorization", "X-Member-Id") // 	브라우저에서 전송할 수 있는 요청 헤더
                .allowCredentials(true) // 	쿠키 등 인증 정보가 포함된 요청 허용
                .maxAge(3600); // 	CORS 사전 요청 결과를 일정 시간 캐시
    }
}
