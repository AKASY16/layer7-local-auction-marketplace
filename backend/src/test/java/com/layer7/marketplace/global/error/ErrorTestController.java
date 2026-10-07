package com.layer7.marketplace.global.error;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * GlobalExceptionHandlerTest에서만 쓰는 컨트롤러. 각 엔드포인트가 일부러 오류를 일으킨다.
 */
@RestController
@RequestMapping("/test/errors")
class ErrorTestController {

	@GetMapping("/business")
	void business() {
		throw new BusinessException(ErrorCode.AUCTION_ENDED);
	}

	@GetMapping("/business-custom-message")
	void businessWithCustomMessage() {
		throw new BusinessException(ErrorCode.BID_AMOUNT_TOO_LOW, "최소 입찰가는 10,500원입니다.");
	}

	@PostMapping("/body")
	void body(@Valid @RequestBody SampleRequest request) {
	}

	@GetMapping("/param")
	void param(@RequestParam @Size(min = 2) String keyword) {
	}

	@GetMapping("/items/{itemId}")
	void item(@PathVariable Long itemId) {
	}

	@GetMapping("/lock")
	void lock() {
		throw new PessimisticLockingFailureException("Lock wait timeout exceeded");
	}

	@GetMapping("/denied")
	void denied() {
		throw new AccessDeniedException("denied");
	}

	@GetMapping("/unexpected")
	void unexpected() {
		throw new IllegalStateException("internal detail that must not leak");
	}

	record SampleRequest(@NotBlank String title, @NotNull @Positive Long amount) {
	}
}
