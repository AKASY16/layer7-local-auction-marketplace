package com.layer7.marketplace.bid.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.layer7.marketplace.support.IntegrationTest;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

class BidIncrementPolicyApiTest extends IntegrationTest {

	@Autowired
	private MockMvcTester mvc;

	@Test
	@DisplayName("로그인 없이 가격단위표 전체를 명세 형식으로 응답한다")
	void returnsWholeTableWithoutLogin() {
		// when
		MvcTestResult result = mvc.get().uri("/api/v1/bid-increment-policy").exchange();

		// then
		assertThat(result)
			.hasStatus(HttpStatus.OK)
			.bodyJson()
			.isStrictlyEqualTo("""
				{
				  "minAmount": 100,
				  "maxAmount": 10000000,
				  "bands": [
				    { "from": 100, "to": 9999, "unit": 100 },
				    { "from": 10000, "to": 49999, "unit": 500 },
				    { "from": 50000, "to": 99999, "unit": 1000 },
				    { "from": 100000, "to": 499999, "unit": 5000 },
				    { "from": 500000, "to": 999999, "unit": 10000 },
				    { "from": 1000000, "to": 10000000, "unit": 20000 }
				  ]
				}
				""");
	}
}
