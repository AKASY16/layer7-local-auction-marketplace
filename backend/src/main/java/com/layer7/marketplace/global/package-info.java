/**
 * 여러 도메인이 함께 쓰는 공통 코드.
 *
 * <p>config(설정), error(ErrorCode, BusinessException, 전역 예외 처리), security(인증 필터, 보안 설정),
 * time(Clock 빈)을 하위 패키지로 둔다. 특정 도메인에만 쓰이는 코드는 여기에 두지 않는다.
 */
package com.layer7.marketplace.global;
