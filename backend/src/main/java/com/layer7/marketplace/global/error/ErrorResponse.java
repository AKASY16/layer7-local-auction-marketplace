package com.layer7.marketplace.global.error;

import java.time.Instant;
import java.util.List;

/**
 * 공통 오류 응답. docs/05-api-spec.md의 "공통 Error Response" 형식이다.
 *
 * <p>Spring Security의 인증 실패(401)·권한 없음(403) 처리처럼 컨트롤러 밖에서 오류 응답을 써야 하는 곳도
 * {@link #of}로 같은 형식을 만든다.
 */
public record ErrorResponse(
		Instant timestamp,
		int status,
		String code,
		String message,
		String path,
		String traceId,
		List<FieldErrorResponse> fieldErrors
) {

	public static ErrorResponse of(ErrorCode errorCode, String path, Instant timestamp) {
		return of(errorCode, errorCode.getMessage(), path, timestamp, List.of());
	}

	public static ErrorResponse of(ErrorCode errorCode, String message, String path, Instant timestamp) {
		return of(errorCode, message, path, timestamp, List.of());
	}

	public static ErrorResponse of(
			ErrorCode errorCode,
			String message,
			String path,
			Instant timestamp,
			List<FieldErrorResponse> fieldErrors
	) {
		// traceId는 요청 추적(로그 연동)을 도입할 때 채운다
		return new ErrorResponse(
				timestamp,
				errorCode.getStatus().value(),
				errorCode.name(),
				message,
				path,
				null,
				List.copyOf(fieldErrors)
		);
	}

	/**
	 * 필드 검증 실패 한 건. code는 검증 애노테이션 이름을 대문자 스네이크로 바꾼 값이다 (NotBlank → NOT_BLANK).
	 */
	public record FieldErrorResponse(String field, String code, String message) {
	}
}
