package com.layer7.marketplace.auth.controller;

import com.layer7.marketplace.auth.dto.LoginRequest;
import com.layer7.marketplace.auth.dto.LoginResponse;
import com.layer7.marketplace.auth.dto.SignupRequest;
import com.layer7.marketplace.auth.service.AuthService;
import com.layer7.marketplace.user.dto.UserResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

	private final AuthService authService;

	public AuthController(AuthService authService) {
		this.authService = authService;
	}

	@PostMapping("/signup")
	public ResponseEntity<UserResponse> signup(
		@Valid @RequestBody SignupRequest request
	) {
		UserResponse response = authService.signup(request);

		return ResponseEntity.status(HttpStatus.CREATED)
			.body(response);
	}

	@PostMapping("/login")
	public ResponseEntity<LoginResponse> login(
		@Valid @RequestBody LoginRequest request
	) {
		LoginResponse response = authService.login(request);

		return ResponseEntity.ok(response);
	}
}
