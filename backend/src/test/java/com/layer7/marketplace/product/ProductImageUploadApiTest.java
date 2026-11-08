package com.layer7.marketplace.product;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.jayway.jsonpath.JsonPath;
import com.layer7.marketplace.global.security.JwtTokenProvider;
import com.layer7.marketplace.support.IntegrationTest;
import com.layer7.marketplace.support.TestFixtures;
import java.net.URI;
import java.net.URLDecoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

class ProductImageUploadApiTest extends IntegrationTest {

	@Autowired private MockMvc mvc;
	@Autowired private TestFixtures fixtures;
	@Autowired private JwtTokenProvider tokens;
	@Autowired private JdbcTemplate jdbc;

	@Test
	@DisplayName("허용 형식의 URL을 10분 서명으로 발급하고 PENDING 기록과 Content-Type 헤더를 반환한다")
	void issueSignedUrls() throws Exception {
		// given
		var user = fixtures.user();
		String token = tokens.createAccessToken(user.getId()).getTokenValue();
		Instant before = Instant.now(clock);
		// when
		String body = mvc.perform(post("/api/v1/uploads/product-images")
			.header(HttpHeaders.AUTHORIZATION, "Bearer " + token).contentType(MediaType.APPLICATION_JSON)
			.content("""
				{"files":[{"contentType":"image/jpeg","size":1},
				{"contentType":"image/png","size":10485760},{"contentType":"image/webp","size":3}]}
				"""))
			.andExpect(status().isCreated()).andExpect(jsonPath("$.uploads.length()").value(3))
			.andExpect(jsonPath("$.uploads[0].headers['Content-Type']").value("image/jpeg"))
			.andReturn().getResponse().getContentAsString();
		// then
		List<String> keys = JsonPath.read(body, "$.uploads[*].objectKey");
		assertThat(keys).doesNotHaveDuplicates().allMatch(key -> key.matches("uploads/[0-9a-f-]{36}"));
		String url = JsonPath.read(body, "$.uploads[0].uploadUrl");
		String decoded = URLDecoder.decode(url, StandardCharsets.UTF_8);
		assertThat(decoded).contains("X-Amz-Expires=600", "X-Amz-SignedHeaders=content-type;host");
		Instant expiresAt = Instant.parse(JsonPath.read(body, "$.uploads[0].expiresAt"));
		assertThat(expiresAt).isBetween(before.plusSeconds(598), Instant.now(clock).plusSeconds(601));
		assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM image_uploads WHERE user_id = ? AND status = 'PENDING'",
			Long.class, user.getId())).isEqualTo(3);
		try (HttpClient http = HttpClient.newHttpClient()) {
			// 다른 Content-Type으로 바꾸면 실제 SeaweedFS의 서명 검증에서 거절된다.
			var response = http.send(HttpRequest.newBuilder(URI.create(url)).header("Content-Type", "image/png")
				.PUT(HttpRequest.BodyPublishers.ofString("x")).build(), HttpResponse.BodyHandlers.ofString());
			assertThat(response.statusCode()).isEqualTo(403);
		}
	}

	@ParameterizedTest
	@ValueSource(strings = {"{\"files\":[]}", "{}", "{\"files\":[null]}",
		"{\"files\":[{\"contentType\":\"image/gif\",\"size\":1}]}",
		"{\"files\":[{\"contentType\":\"image/png\",\"size\":0}]}",
		"{\"files\":[{\"contentType\":\"image/png\",\"size\":10485761}]}",
		"{\"files\":[{\"size\":1}]}", "{\"files\":[{\"contentType\":\"image/png\"}]}"})
	@DisplayName("개수·형식·크기 오류는 기록 없이 VALIDATION_ERROR로 거절한다")
	void invalidFiles(String body) throws Exception {
		// given
		var user = fixtures.user();
		String token = tokens.createAccessToken(user.getId()).getTokenValue();
		// when / then
		mvc.perform(post("/api/v1/uploads/product-images").header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
			.contentType(MediaType.APPLICATION_JSON).content(body))
			.andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
		assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM image_uploads WHERE user_id = ?", Long.class, user.getId()))
			.isZero();
	}

	@Test
	@DisplayName("파일 10개는 허용하고 11개와 탈퇴 회원은 거절한다")
	void countLimitAndWithdrawn() throws Exception {
		// given
		var user = fixtures.user();
		String token = tokens.createAccessToken(user.getId()).getTokenValue();
		String file = "{\"contentType\":\"image/png\",\"size\":1}";
		// when / then
		for (int count : List.of(10, 11)) {
			var result = mvc.perform(post("/api/v1/uploads/product-images")
				.header(HttpHeaders.AUTHORIZATION, "Bearer " + token).contentType(MediaType.APPLICATION_JSON)
				.content("{\"files\":[" + String.join(",", Collections.nCopies(count, file)) + "]}"));
			if (count == 10) result.andExpect(status().isCreated());
			else result.andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
		}
		fixtures.withdraw(user.getId());
		mvc.perform(post("/api/v1/uploads/product-images").header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
			.contentType(MediaType.APPLICATION_JSON).content("{\"files\":[" + file + "]}"))
			.andExpect(status().isForbidden()).andExpect(jsonPath("$.code").value("ACCOUNT_WITHDRAWN"));
	}
}
