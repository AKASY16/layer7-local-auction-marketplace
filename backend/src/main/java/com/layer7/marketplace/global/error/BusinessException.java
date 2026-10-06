package com.layer7.marketplace.global.error;

import lombok.Getter;

/**
 * 비즈니스 규칙 위반을 알리는 예외. 응답 형식은 {@link GlobalExceptionHandler}가 만든다.
 *
 * <pre>{@code
 * throw new BusinessException(ErrorCode.AUCTION_ENDED);
 * throw new BusinessException(ErrorCode.BID_AMOUNT_TOO_LOW, "최소 입찰가는 10,500원입니다.");
 * }</pre>
 */
@Getter
public class BusinessException extends RuntimeException {

	private final ErrorCode errorCode;

	public BusinessException(ErrorCode errorCode) {
		super(errorCode.getMessage());
		this.errorCode = errorCode;
	}

	/**
	 * 기본 메시지 대신 상황에 맞는 메시지를 보낼 때 쓴다. 프론트는 message가 아니라 code로 분기한다.
	 */
	public BusinessException(ErrorCode errorCode, String message) {
		super(message);
		this.errorCode = errorCode;
	}
}
