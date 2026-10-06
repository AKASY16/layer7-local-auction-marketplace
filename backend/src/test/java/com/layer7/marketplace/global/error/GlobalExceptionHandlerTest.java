package com.layer7.marketplace.global.error;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

// 보안 필터는 SecurityConfig(#23)의 몫이라 여기서는 끄고, 컨트롤러에서 올라온 예외의 응답 형식만 본다
@WebMvcTest(controllers = ErrorTestController.class)
@AutoConfigureMockMvc(addFilters = false)
@Import(GlobalExceptionHandlerTest.FixedClockConfig.class)
class GlobalExceptionHandlerTest {

	private static final Instant NOW = Instant.parse("2026-10-07T03:00:00Z");

	@Autowired
	private MockMvcTester mvc;

	@TestConfiguration
	static class FixedClockConfig {

		@Bean
		Clock clock() {
			return Clock.fixed(NOW, ZoneOffset.UTC);
		}
	}

	@Test
	@DisplayName("BusinessException은 05 명세의 공통 Error Response 형식으로 응답한다")
	void businessException() {
		assertThat(mvc.get().uri("/test/errors/business"))
				.hasStatus(HttpStatus.CONFLICT)
				.bodyJson()
				.isStrictlyEqualTo("""
						{
						  "timestamp": "2026-10-07T03:00:00Z",
						  "status": 409,
						  "code": "AUCTION_ENDED",
						  "message": "종료된 경매에는 입찰할 수 없습니다.",
						  "path": "/test/errors/business",
						  "traceId": null,
						  "fieldErrors": []
						}
						""");
	}

	@Test
	@DisplayName("BusinessException에 메시지를 주면 기본 메시지 대신 그 메시지로 응답한다")
	void businessExceptionWithCustomMessage() {
		assertThat(mvc.get().uri("/test/errors/business-custom-message"))
				.hasStatus(HttpStatus.CONFLICT)
				.bodyJson()
				.isLenientlyEqualTo("""
						{ "code": "BID_AMOUNT_TOO_LOW", "message": "최소 입찰가는 10,500원입니다." }
						""");
	}

	@Test
	@DisplayName("요청 본문 검증에 실패하면 VALIDATION_ERROR와 필드별 오류를 응답한다")
	void requestBodyValidation() {
		// 필드 오류 message는 JVM 언어 설정에 따라 바뀌므로 field와 code만 확인한다
		assertThat(mvc.post().uri("/test/errors/body")
				.contentType(MediaType.APPLICATION_JSON)
				.content("""
						{ "title": "", "amount": -1 }
						"""))
				.hasStatus(HttpStatus.BAD_REQUEST)
				.bodyJson()
				.isLenientlyEqualTo("""
						{
						  "status": 400,
						  "code": "VALIDATION_ERROR",
						  "message": "요청 값을 확인해주세요.",
						  "fieldErrors": [
						    { "field": "title", "code": "NOT_BLANK" },
						    { "field": "amount", "code": "POSITIVE" }
						  ]
						}
						""");
	}

	@Test
	@DisplayName("쿼리 값 검증에 실패하면 파라미터 이름을 field로 응답한다")
	void requestParamValidation() {
		assertThat(mvc.get().uri("/test/errors/param").param("keyword", "a"))
				.hasStatus(HttpStatus.BAD_REQUEST)
				.bodyJson()
				.isLenientlyEqualTo("""
						{
						  "code": "VALIDATION_ERROR",
						  "fieldErrors": [ { "field": "keyword", "code": "SIZE" } ]
						}
						""");
	}

	@Test
	@DisplayName("JSON 문법이 틀리면 VALIDATION_ERROR와 본문을 읽을 수 없다는 메시지로 응답한다")
	void malformedJson() {
		assertThat(mvc.post().uri("/test/errors/body")
				.contentType(MediaType.APPLICATION_JSON)
				.content("{ \"title\": "))
				.hasStatus(HttpStatus.BAD_REQUEST)
				.bodyJson()
				.isLenientlyEqualTo("""
						{
						  "code": "VALIDATION_ERROR",
						  "message": "요청 본문을 읽을 수 없습니다. JSON 형식과 값의 타입을 확인해주세요."
						}
						""");
	}

	@Test
	@DisplayName("경로 값의 타입이 틀리면 VALIDATION_ERROR로 응답한다")
	void pathVariableTypeMismatch() {
		assertThat(mvc.get().uri("/test/errors/items/abc"))
				.hasStatus(HttpStatus.BAD_REQUEST)
				.bodyJson()
				.isLenientlyEqualTo("""
						{ "status": 400, "code": "VALIDATION_ERROR", "path": "/test/errors/items/abc" }
						""");
	}

	@Test
	@DisplayName("없는 주소는 RESOURCE_NOT_FOUND로 응답한다")
	void noResource() {
		assertThat(mvc.get().uri("/test/errors/nowhere"))
				.hasStatus(HttpStatus.NOT_FOUND)
				.bodyJson()
				.isLenientlyEqualTo("""
						{ "status": 404, "code": "RESOURCE_NOT_FOUND" }
						""");
	}

	@Test
	@DisplayName("지원하지 않는 HTTP 메서드는 METHOD_NOT_ALLOWED로 응답한다")
	void methodNotAllowed() {
		assertThat(mvc.post().uri("/test/errors/business"))
				.hasStatus(HttpStatus.METHOD_NOT_ALLOWED)
				.bodyJson()
				.isLenientlyEqualTo("""
						{ "status": 405, "code": "METHOD_NOT_ALLOWED" }
						""");
	}

	@Test
	@DisplayName("지원하지 않는 Content-Type은 UNSUPPORTED_MEDIA_TYPE으로 응답한다")
	void unsupportedMediaType() {
		assertThat(mvc.post().uri("/test/errors/body")
				.contentType(MediaType.TEXT_PLAIN)
				.content("title"))
				.hasStatus(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
				.bodyJson()
				.isLenientlyEqualTo("""
						{ "status": 415, "code": "UNSUPPORTED_MEDIA_TYPE" }
						""");
	}

	@Test
	@DisplayName("락 대기 시간을 넘기면 재시도할 수 있는 RESOURCE_BUSY(503)로 응답한다")
	void lockWaitTimeout() {
		assertThat(mvc.get().uri("/test/errors/lock"))
				.hasStatus(HttpStatus.SERVICE_UNAVAILABLE)
				.bodyJson()
				.isLenientlyEqualTo("""
						{ "status": 503, "code": "RESOURCE_BUSY" }
						""");
	}

	@Test
	@DisplayName("서비스에서 나온 권한 예외는 500이 아니라 FORBIDDEN으로 응답한다")
	void accessDenied() {
		assertThat(mvc.get().uri("/test/errors/denied"))
				.hasStatus(HttpStatus.FORBIDDEN)
				.bodyJson()
				.isLenientlyEqualTo("""
						{ "status": 403, "code": "FORBIDDEN" }
						""");
	}

	@Test
	@DisplayName("예상하지 못한 예외는 INTERNAL_ERROR로 응답하고 내부 메시지를 노출하지 않는다")
	void unexpectedException() {
		var result = mvc.get().uri("/test/errors/unexpected").exchange();

		assertThat(result)
				.hasStatus(HttpStatus.INTERNAL_SERVER_ERROR)
				.bodyJson()
				.isLenientlyEqualTo("""
						{
						  "status": 500,
						  "code": "INTERNAL_ERROR",
						  "message": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
						}
						""");
		assertThat(result).bodyText().doesNotContain("internal detail");
	}

	@Test
	@DisplayName("검증 애노테이션 이름을 대문자 스네이크 코드로 바꾼다")
	void toCode() {
		assertThat(GlobalExceptionHandler.toCode("NotBlank")).isEqualTo("NOT_BLANK");
		assertThat(GlobalExceptionHandler.toCode("Size")).isEqualTo("SIZE");
		assertThat(GlobalExceptionHandler.toCode("typeMismatch")).isEqualTo("TYPE_MISMATCH");
		assertThat(GlobalExceptionHandler.toCode(null)).isEqualTo("INVALID");
	}
}
