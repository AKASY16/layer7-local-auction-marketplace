package com.layer7.marketplace.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import com.layer7.marketplace.global.validation.Utf8ByteLength;

public record SignupRequest(
	@NotBlank @Email @Size(max = 320) String email,
	@NotBlank @Utf8ByteLength(max = 72) String password,
	@NotBlank @Size(max = 50) String nickname,
	@NotNull @Positive Long regionId
) {
}
