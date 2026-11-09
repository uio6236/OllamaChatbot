package com.hoperefund.common.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.web.servlet.MockMvc;

/**
 * 서버 상태 확인 API 테스트
 * /api/health 요청의 정상 응답 여부를 검증한다.
 */
@WebMvcTest(HealthController.class) // Controller 중심의 테스트 환경 구성
@AutoConfigureMockMvc(addFilters = false)
class HealthControllerTest {

    @Autowired // Spring이 생성한 MockMvc 주입
    private MockMvc mockMvc;

    @Test // JUnit이 실행할 테스트 메서드
    void healthApiReturnsOk() throws Exception {

        mockMvc.perform(get("/api/health")) // 가상의 HTTP 요청 실행
                .andExpect(status().isOk()) // HTTP 200인지 확인
                .andExpect(content().string("OK"));
    }
}
