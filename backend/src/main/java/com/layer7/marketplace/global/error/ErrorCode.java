package com.layer7.marketplace.global.error;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

/**
 * API 오류 코드. docs/05-api-spec.md의 "주요 Error Code" 표와 1:1로 대응한다.
 *
 * <p>코드를 추가하거나 바꿀 때는 명세 표도 같은 PR에서 함께 고친다. {@code ErrorCodeSpecTest}가 둘이 어긋나면 실패한다.
 */
@Getter
@RequiredArgsConstructor
public enum ErrorCode {

	// 400
	VALIDATION_ERROR(HttpStatus.BAD_REQUEST, "요청 값을 확인해주세요."),
	INVALID_PRICE_UNIT(HttpStatus.BAD_REQUEST, "가격 단위에 맞지 않는 금액입니다."),
	AMOUNT_LIMIT_EXCEEDED(HttpStatus.BAD_REQUEST, "금액은 10,000,000원을 넘을 수 없습니다."),
	INVALID_UPLOAD(HttpStatus.BAD_REQUEST, "업로드한 이미지를 확인할 수 없습니다."),
	AUCTION_PERIOD_INVALID(HttpStatus.BAD_REQUEST, "경매 기간은 1시간 이상 7일 이하, 예약 시작은 7일 이내여야 합니다."),
	IDEMPOTENCY_KEY_REQUIRED(HttpStatus.BAD_REQUEST, "Idempotency-Key 헤더가 필요합니다."),

	// 401
	UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다."),
	INVALID_TOKEN(HttpStatus.UNAUTHORIZED, "인증 정보가 올바르지 않거나 만료되었습니다."),
	INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 일치하지 않습니다."),
	INVALID_REFRESH_TOKEN(HttpStatus.UNAUTHORIZED, "다시 로그인해주세요."),

	// 403
	ACCOUNT_WITHDRAWN(HttpStatus.FORBIDDEN, "탈퇴한 계정입니다."),
	FORBIDDEN(HttpStatus.FORBIDDEN, "권한이 없습니다."),
	SELF_BID_FORBIDDEN(HttpStatus.FORBIDDEN, "본인 경매에는 입찰할 수 없습니다."),
	USER_RESTRICTED(HttpStatus.FORBIDDEN, "거래 참여가 정지된 상태입니다."),
	COMPLETION_SELF_CONFIRM_FORBIDDEN(HttpStatus.FORBIDDEN, "본인이 요청한 거래 완료는 상대방만 확인할 수 있습니다."),

	// 404
	RESOURCE_NOT_FOUND(HttpStatus.NOT_FOUND, "대상을 찾을 수 없습니다."),

	// 405
	METHOD_NOT_ALLOWED(HttpStatus.METHOD_NOT_ALLOWED, "지원하지 않는 요청 방식입니다."),

	// 409
	USER_WITHDRAWAL_BLOCKED(HttpStatus.CONFLICT, "진행 중인 상품·경매·입찰·거래가 있어 탈퇴할 수 없습니다."),
	DUPLICATE_EMAIL(HttpStatus.CONFLICT, "이미 사용 중인 이메일입니다."),
	DUPLICATE_NICKNAME(HttpStatus.CONFLICT, "이미 사용 중인 닉네임입니다."),
	PRODUCT_LOCKED_AFTER_BID(HttpStatus.CONFLICT, "입찰이 있었던 상품은 수정할 수 없습니다."),
	PRODUCT_LOCKED_AUCTION_STARTED(HttpStatus.CONFLICT, "경매가 시작된 상품은 수정할 수 없습니다."),
	PRODUCT_DELETE_NOT_ALLOWED(HttpStatus.CONFLICT, "진행 중인 경매나 거래가 있는 상품은 삭제할 수 없습니다."),
	ACTIVE_AUCTION_ALREADY_EXISTS(HttpStatus.CONFLICT, "이미 진행 중이거나 예약된 경매가 있습니다."),
	AUCTION_NOT_OPEN(HttpStatus.CONFLICT, "입찰할 수 있는 경매가 아닙니다."),
	AUCTION_ENDED(HttpStatus.CONFLICT, "종료된 경매에는 입찰할 수 없습니다."),
	BID_AMOUNT_TOO_LOW(HttpStatus.CONFLICT, "최소 입찰가보다 낮은 금액입니다."),
	ALREADY_LEADING(HttpStatus.CONFLICT, "이미 최고 입찰자입니다. 상한을 올리려면 자동입찰을 사용해주세요."),
	DUPLICATE_BID_AMOUNT(HttpStatus.CONFLICT, "같은 금액의 입찰이 이미 있습니다."),
	AUTO_BID_MAX_TOO_LOW(HttpStatus.CONFLICT, "자동입찰 상한이 현재 최소 입찰가보다 낮습니다."),
	PRODUCT_IMAGE_LIMIT(HttpStatus.CONFLICT, "상품 이미지는 최대 10장까지 등록할 수 있습니다."),
	PRODUCT_IMAGE_REQUIRED(HttpStatus.CONFLICT, "상품 이미지는 최소 1장이 필요합니다."),
	PRODUCT_APPEND_LIMIT(HttpStatus.CONFLICT, "내용 추가는 경매당 최대 10건까지 할 수 있습니다."),
	AUCTION_RELIST_NOT_ALLOWED(HttpStatus.CONFLICT, "지금은 재경매할 수 없습니다."),
	AUCTION_CANNOT_CANCEL(HttpStatus.CONFLICT, "입찰이 있는 경매는 취소할 수 없습니다."),
	TRADE_INVALID_STATE(HttpStatus.CONFLICT, "지금 거래 상태에서는 할 수 없는 요청입니다."),
	TRADE_RESPONSE_EXPIRED(HttpStatus.CONFLICT, "낙찰 응답 기한이 지났습니다."),
	TRADE_DEADLINE_PASSED(HttpStatus.CONFLICT, "거래 기한이 지났습니다."),
	IDEMPOTENCY_KEY_REUSED(HttpStatus.CONFLICT, "이미 다른 요청에 사용한 Idempotency-Key입니다."),

	// 415
	UNSUPPORTED_MEDIA_TYPE(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "지원하지 않는 Content-Type입니다."),

	// 500
	INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."),

	// 503
	RESOURCE_BUSY(HttpStatus.SERVICE_UNAVAILABLE, "요청이 몰려 처리하지 못했습니다. 잠시 후 다시 시도해주세요.");

	private final HttpStatus status;
	private final String message;
}
