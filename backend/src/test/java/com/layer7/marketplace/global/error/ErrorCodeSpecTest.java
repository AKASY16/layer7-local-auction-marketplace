package com.layer7.marketplace.global.error;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * ErrorCode enum과 API 명세의 오류 코드 표가 어긋나지 않는지 확인한다.
 * 코드를 추가·변경할 때 명세를 함께 고치지 않으면 이 테스트가 실패한다.
 */
class ErrorCodeSpecTest {

	// Gradle은 backend 폴더에서 테스트를 실행하므로 저장소 루트의 docs는 한 단계 위에 있다
	private static final Path API_SPEC = Path.of("..", "docs", "05-api-spec.md");
	private static final Pattern CODE_ROW = Pattern.compile("^\\|\\s*([A-Z][A-Z0-9_]+)\\s*\\|\\s*(\\d{3})\\s*\\|");

	@Test
	@DisplayName("ErrorCode와 05 명세의 주요 Error Code 표는 코드와 HTTP 상태가 같다")
	void errorCodesMatchApiSpec() throws IOException {
		Map<String, Integer> spec = readSpecCodes();
		Map<String, Integer> code = Arrays.stream(ErrorCode.values())
				.collect(Collectors.toMap(Enum::name, e -> e.getStatus().value(), (a, b) -> a, LinkedHashMap::new));

		assertThat(spec).as("명세 표가 비어 있으면 표 형식이 바뀐 것").isNotEmpty();
		assertThat(code).isEqualTo(spec);
	}

	private static Map<String, Integer> readSpecCodes() throws IOException {
		List<String> lines = Files.readAllLines(API_SPEC, StandardCharsets.UTF_8);
		Map<String, Integer> codes = new LinkedHashMap<>();
		boolean inTable = false;
		for (String line : lines) {
			if (line.startsWith("## ")) {
				inTable = line.equals("## 주요 Error Code");
				continue;
			}
			Matcher matcher = CODE_ROW.matcher(line);
			if (inTable && matcher.find()) {
				codes.put(matcher.group(1), Integer.parseInt(matcher.group(2)));
			}
		}
		return codes;
	}
}
