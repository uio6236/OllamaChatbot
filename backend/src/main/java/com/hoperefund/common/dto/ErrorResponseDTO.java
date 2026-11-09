package com.hoperefund.common.dto;

/**
 * 공통 API 오류 응답 DTO
 * 모든 API 오류를 error, message 형식으로 반환한다.
 */
public record ErrorResponseDTO(String error, String message) {}
