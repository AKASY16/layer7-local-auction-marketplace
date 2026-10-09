package com.layer7.marketplace.global.validation;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;
import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Documented
@Constraint(validatedBy = Utf8ByteLengthValidator.class)
@Target({
	ElementType.FIELD,
	ElementType.METHOD,
	ElementType.PARAMETER,
	ElementType.RECORD_COMPONENT
})
@Retention(RetentionPolicy.RUNTIME)
public @interface Utf8ByteLength {

	String message() default "UTF-8 기준 {max}바이트 이하여야 합니다.";

	Class<?>[] groups() default {};

	Class<? extends Payload>[] payload() default {};

	int max();
}
