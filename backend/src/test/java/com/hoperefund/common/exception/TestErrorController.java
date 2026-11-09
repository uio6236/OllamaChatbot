package com.hoperefund.common.exception;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * 공통 예외 처리 테스트를 위한 전용 Controller
 * 잘못된 JSON과 서버 내부 예외 상황을 재현한다.
 * 실제 서비스 API로 등록하지 않는다.
 */
@RestController
public class TestErrorController {

    @PostMapping("/api/test-errors/json")
    public String invalidJson(@RequestBody TestRequest request) {
        return request.content();
    }

    @GetMapping("/api/test-errors/server")
    public String serverError() {
        throw new IllegalStateException("테스트용 오류");
    }

    public record TestRequest(String content) {}
}
