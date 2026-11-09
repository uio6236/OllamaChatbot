package com.hoperefund.common.config;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.hoperefund.common.controller.HealthController;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

/**
 * React 와 Spring Boot 간 CORS 설정 테스트
 * 허용된 출처와 허용되지 않은 출처를 검증한다.
 * TODO: Spring Security 적용 후 인증 환경에서 재검증
 */
@WebMvcTest(HealthController.class)
@AutoConfigureMockMvc(addFilters = false)
@Import(CorsConfig.class)
class CorsConfigTest {

    @Autowired private MockMvc mockMvc;

    @Test
    void allowedOriginReturnsCorsHeaders() throws Exception {

        mockMvc.perform(
                        options("/api/health")
                                .header("Origin", "http://localhost:5173")
                                .header("Access-Control-Request-Method", "GET")
                                .header("Access-Control-Request-Headers", "X-Member-Id"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:5173"));
    }

    @Test
    void disallowedOriginIsRejected() throws Exception {

        mockMvc.perform(
                        options("/api/health")
                                .header("Origin", "http://localhost:9999")
                                .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isForbidden());
    }
}
