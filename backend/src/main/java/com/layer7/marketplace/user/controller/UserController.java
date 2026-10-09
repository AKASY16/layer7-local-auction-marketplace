package com.layer7.marketplace.user.controller;

import com.layer7.marketplace.global.error.BusinessException;
import com.layer7.marketplace.global.error.ErrorCode;
import com.layer7.marketplace.global.security.AuthenticatedUser;
import com.layer7.marketplace.user.dto.UserMeResponse;
import com.layer7.marketplace.user.service.UserService;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/users")
public class UserController {

	private final UserService userService;

	public UserController(UserService userService) {
		this.userService = userService;
	}

	@GetMapping("/me")
	public UserMeResponse getMe(
		@AuthenticationPrincipal AuthenticatedUser user
	) {
		if (user == null) {
			throw new BusinessException(ErrorCode.UNAUTHORIZED);
		}

		return userService.getMe(user.userId());
	}
}
