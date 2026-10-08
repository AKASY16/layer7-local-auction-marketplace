package com.layer7.marketplace;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@Import(TestcontainersConfiguration.class)
class RegionApiTest {

	@Autowired
	private MockMvc mockMvc;

	@Autowired
	private JdbcTemplate jdbcTemplate;

	@Test
	@DisplayName("로그인 없이 성동구를 검색하고 공통 Region 형식으로 응답한다")
	void searchWithoutLogin() throws Exception {
		// given
		String query = "성동";

		// when
		var result = mockMvc.perform(
			get("/api/v1/regions").param("query", query)
		);

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.content.length()").value(1))
			.andExpect(jsonPath("$.content[0].id").isNumber())
			.andExpect(jsonPath("$.content[0].regionCode").value("11200"))
			.andExpect(jsonPath("$.content[0].sidoName").value("서울특별시"))
			.andExpect(jsonPath("$.content[0].sigunguName").value("성동구"))
			.andExpect(jsonPath("$.page").value(0))
			.andExpect(jsonPath("$.size").value(20))
			.andExpect(jsonPath("$.totalElements").value(1))
			.andExpect(jsonPath("$.totalPages").value(1));
	}

	@Test
	@DisplayName("검색어 앞뒤의 공백을 제거한다")
	void trimQuery() throws Exception {
		// given
		String query = "  성동  ";

		// when
		var result = mockMvc.perform(
			get("/api/v1/regions").param("query", query)
		);

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.content[0].regionCode").value("11200"))
			.andExpect(jsonPath("$.totalElements").value(1));
	}

	@Test
	@DisplayName("검색 결과가 없으면 200과 빈 목록을 반환한다")
	void noMatches() throws Exception {
		// given
		String query = "없는지역테스트";

		// when
		var result = mockMvc.perform(
			get("/api/v1/regions").param("query", query)
		);

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.content").isEmpty())
			.andExpect(jsonPath("$.totalElements").value(0))
			.andExpect(jsonPath("$.totalPages").value(0));
	}

	@Test
	@DisplayName("검색어를 생략하면 전체 지역의 첫 페이지를 반환한다")
	void missingQuery() throws Exception {
		// given
		int expectedRegionCount = 230;

		// when
		var result = mockMvc.perform(get("/api/v1/regions"));

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.content.length()").value(20))
			.andExpect(jsonPath("$.page").value(0))
			.andExpect(jsonPath("$.size").value(20))
			.andExpect(jsonPath("$.totalElements").value(expectedRegionCount))
			.andExpect(jsonPath("$.totalPages").value(12));
	}

	@Test
	@DisplayName("공백 검색어는 전체 지역 조회로 처리한다")
	void blankQuery() throws Exception {
		// given
		String query = "   ";

		// when
		var result = mockMvc.perform(
			get("/api/v1/regions").param("query", query)
		);

		// then
		result
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.content.length()").value(20))
			.andExpect(jsonPath("$.totalElements").value(230));
	}

	@Test
	@DisplayName("페이지 크기가 50을 넘으면 공통 검증 오류를 반환한다")
	void invalidPageSize() throws Exception {
		// given
		String size = "51";

		// when
		var result = mockMvc.perform(
			get("/api/v1/regions").param("size", size)
		);

		// then
		result
			.andExpect(status().isBadRequest())
			.andExpect(jsonPath("$.code").value("VALIDATION_ERROR"));
	}

	@Test
	@DisplayName("새 MySQL에 Flyway V1과 V2가 적용되고 지역 시드가 저장된다")
	void migrationsAndSeeds() {
		// given
		String migrationSql = """
				SELECT COUNT(*)
				FROM flyway_schema_history
				WHERE version IN ('1', '2') AND success = 1
				""";

		// when
		Long migrationCount = jdbcTemplate.queryForObject(
			migrationSql, Long.class
		);
		Long regionCount = jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM regions", Long.class
		);
		String suwonName = jdbcTemplate.queryForObject(
			"SELECT sigungu_name FROM regions WHERE region_code = '41110'",
			String.class
		);
		Long janganCount = jdbcTemplate.queryForObject(
			"SELECT COUNT(*) FROM regions WHERE region_code = '41111'",
			Long.class
		);

		// then
		assertThat(migrationCount).isEqualTo(2L);
		assertThat(regionCount).isEqualTo(230L);
		assertThat(suwonName).isEqualTo("수원시");
		assertThat(janganCount).isZero();
	}
}
