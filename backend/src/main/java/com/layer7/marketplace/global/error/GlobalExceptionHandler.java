package com.layer7.marketplace.global.error;

import com.layer7.marketplace.global.error.ErrorResponse.FieldErrorResponse;
import jakarta.servlet.http.HttpServletRequest;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.stream.Stream;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.MessageSourceResolvable;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.validation.FieldError;
import org.springframework.validation.method.ParameterValidationResult;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.ServletWebRequest;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * 컨트롤러에서 올라온 모든 예외를 공통 오류 응답({@link ErrorResponse})으로 바꾼다.
 *
 * <p>ResponseEntityExceptionHandler를 상속해 잘못된 JSON, 없는 주소, 지원하지 않는 메서드 같은 Spring MVC 예외도
 * {@link #handleExceptionInternal}에서 같은 형식으로 응답한다.
 */
@Slf4j
@RestControllerAdvice
@RequiredArgsConstructor
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

	private static final String UNREADABLE_BODY_MESSAGE =
		"요청 본문을 읽을 수 없습니다. JSON 형식과 값의 타입을 확인해주세요.";

	private final Clock clock;

	@ExceptionHandler(BusinessException.class)
	public ResponseEntity<ErrorResponse> handleBusinessException(
		BusinessException e,
		HttpServletRequest request
	) {
		log.info(
			"[{}] {} {} - {}",
			e.getErrorCode(),
			request.getMethod(),
			request.getRequestURI(),
			e.getMessage()
		);

		return respond(
			ErrorResponse.of(
				e.getErrorCode(),
				e.getMessage(),
				request.getRequestURI(),
				now()
			)
		);
	}

	// 락 대기 시간 초과는 같은 Idempotency-Key로 다시 시도할 수 있는 503
	@ExceptionHandler(PessimisticLockingFailureException.class)
	public ResponseEntity<ErrorResponse> handleLockFailure(
		PessimisticLockingFailureException e,
		HttpServletRequest request
	) {
		log.warn(
			"[{}] {} {} - {}",
			ErrorCode.RESOURCE_BUSY,
			request.getMethod(),
			request.getRequestURI(),
			e.getMessage()
		);

		return respond(
			ErrorResponse.of(
				ErrorCode.RESOURCE_BUSY,
				request.getRequestURI(),
				now()
			)
		);
	}

	// 서비스 계층의 권한 검사에서 나온 보안 예외를 공통 403 응답으로 바꾼다.
	// 필터 단계의 오류도 SecurityConfig가 이 처리기로 넘긴다.
	@ExceptionHandler(AccessDeniedException.class)
	public ResponseEntity<ErrorResponse> handleAccessDenied(
		AccessDeniedException e,
		HttpServletRequest request
	) {
		log.info(
			"[{}] {} {}",
			ErrorCode.FORBIDDEN,
			request.getMethod(),
			request.getRequestURI()
		);

		return respond(
			ErrorResponse.of(
				ErrorCode.FORBIDDEN,
				request.getRequestURI(),
				now()
			)
		);
	}

	@ExceptionHandler(AuthenticationException.class)
	public ResponseEntity<ErrorResponse> handleAuthentication(
		AuthenticationException e,
		HttpServletRequest request
	) {
		log.info(
			"[{}] {} {}",
			ErrorCode.UNAUTHORIZED,
			request.getMethod(),
			request.getRequestURI()
		);

		return respond(
			ErrorResponse.of(
				ErrorCode.UNAUTHORIZED,
				request.getRequestURI(),
				now()
			)
		);
	}

	// 예상하지 못한 오류. 내부 메시지는 응답에 노출하지 않고 로그로만 남긴다.
	@ExceptionHandler(Exception.class)
	public ResponseEntity<ErrorResponse> handleUnexpected(
		Exception e,
		HttpServletRequest request
	) {
		log.error(
			"[{}] {} {}",
			ErrorCode.INTERNAL_ERROR,
			request.getMethod(),
			request.getRequestURI(),
			e
		);

		return respond(
			ErrorResponse.of(
				ErrorCode.INTERNAL_ERROR,
				request.getRequestURI(),
				now()
			)
		);
	}

	// @Valid가 붙은 요청 본문의 검증 실패
	@Override
	protected ResponseEntity<Object> handleMethodArgumentNotValid(
		MethodArgumentNotValidException ex,
		HttpHeaders headers,
		HttpStatusCode status,
		WebRequest request
	) {
		List<FieldErrorResponse> fieldErrors =
			ex.getBindingResult().getFieldErrors().stream()
				.map(error -> new FieldErrorResponse(
					error.getField(),
					toCode(error.getCode()),
					error.getDefaultMessage()
				))
				.toList();

		return handleExceptionInternal(
			ex,
			validationError(fieldErrors, request),
			headers,
			status,
			request
		);
	}

	// 경로·쿼리 값(@RequestParam, @PathVariable 등)에 붙은 제약의 검증 실패
	@Override
	protected ResponseEntity<Object> handleHandlerMethodValidationException(
		HandlerMethodValidationException ex,
		HttpHeaders headers,
		HttpStatusCode status,
		WebRequest request
	) {
		List<FieldErrorResponse> fieldErrors =
			ex.getParameterValidationResults().stream()
				.flatMap(GlobalExceptionHandler::toFieldErrors)
				.toList();

		return handleExceptionInternal(
			ex,
			validationError(fieldErrors, request),
			headers,
			status,
			request
		);
	}

	// JSON 문법 오류, 값 타입 불일치 등 본문을 읽지 못한 경우
	@Override
	protected ResponseEntity<Object> handleHttpMessageNotReadable(
		HttpMessageNotReadableException ex,
		HttpHeaders headers,
		HttpStatusCode status,
		WebRequest request
	) {
		ErrorResponse body = ErrorResponse.of(
			ErrorCode.VALIDATION_ERROR,
			UNREADABLE_BODY_MESSAGE,
			path(request),
			now()
		);

		return handleExceptionInternal(
			ex,
			body,
			headers,
			status,
			request
		);
	}

	/**
	 * Spring MVC 예외가 모두 거쳐 가는 곳.
	 * 위에서 응답을 만든 경우는 그대로 쓰고, 나머지는 HTTP 상태로 ErrorCode를 고른다.
	 */
	@Override
	protected ResponseEntity<Object> handleExceptionInternal(
		Exception ex,
		Object body,
		HttpHeaders headers,
		HttpStatusCode statusCode,
		WebRequest request
	) {
		ErrorResponse errorResponse = body instanceof ErrorResponse given
			? given
			: ErrorResponse.of(
			errorCodeFor(statusCode),
			path(request),
			now()
		);

		if (errorResponse.status() >= 500) {
			log.error(
				"[{}] {}",
				errorResponse.code(),
				errorResponse.path(),
				ex
			);
		} else {
			log.info(
				"[{}] {} - {}",
				errorResponse.code(),
				errorResponse.path(),
				ex.getMessage()
			);
		}

		return super.handleExceptionInternal(
			ex,
			errorResponse,
			headers,
			HttpStatusCode.valueOf(errorResponse.status()),
			request
		);
	}

	private static ErrorCode errorCodeFor(HttpStatusCode statusCode) {
		return switch (statusCode.value()) {
			case 400 -> ErrorCode.VALIDATION_ERROR;
			case 401 -> ErrorCode.UNAUTHORIZED;
			case 403 -> ErrorCode.FORBIDDEN;
			case 404 -> ErrorCode.RESOURCE_NOT_FOUND;
			case 405 -> ErrorCode.METHOD_NOT_ALLOWED;
			case 415 -> ErrorCode.UNSUPPORTED_MEDIA_TYPE;
			case 503 -> ErrorCode.RESOURCE_BUSY;
			default -> statusCode.is4xxClientError()
				? ErrorCode.VALIDATION_ERROR
				: ErrorCode.INTERNAL_ERROR;
		};
	}

	private static Stream<FieldErrorResponse> toFieldErrors(
		ParameterValidationResult result
	) {
		String parameterName =
			result.getMethodParameter().getParameterName();

		return result.getResolvableErrors().stream()
			.map(error -> error instanceof FieldError fieldError
				? new FieldErrorResponse(
				fieldError.getField(),
				toCode(fieldError.getCode()),
				fieldError.getDefaultMessage()
			)
				: new FieldErrorResponse(
				parameterName,
				toCode(lastCode(error)),
				error.getDefaultMessage()
			));
	}

	// 검증 코드 목록의 마지막 값이 애너테이션 이름이다.
	private static String lastCode(MessageSourceResolvable error) {
		String[] codes = error.getCodes();

		return codes == null || codes.length == 0
			? null
			: codes[codes.length - 1];
	}

	// 검증 애너테이션 이름을 대문자 스네이크로 바꾼다: NotBlank → NOT_BLANK
	static String toCode(String annotationName) {
		if (annotationName == null || annotationName.isBlank()) {
			return "INVALID";
		}

		return annotationName
			.replaceAll("([a-z0-9])([A-Z])", "$1_$2")
			.toUpperCase();
	}

	private ErrorResponse validationError(
		List<FieldErrorResponse> fieldErrors,
		WebRequest request
	) {
		ErrorCode code = ErrorCode.VALIDATION_ERROR;

		return ErrorResponse.of(
			code,
			code.getMessage(),
			path(request),
			now(),
			fieldErrors
		);
	}

	private static String path(WebRequest request) {
		if (request instanceof ServletWebRequest servletWebRequest) {
			return servletWebRequest.getRequest().getRequestURI();
		}

		return request.getDescription(false).replace("uri=", "");
	}

	private Instant now() {
		return Instant.now(clock);
	}

	private static ResponseEntity<ErrorResponse> respond(ErrorResponse body) {
		return ResponseEntity.status(body.status()).body(body);
	}
}
