# Backend 코드 컨벤션

세 명이 같은 방식으로 코드를 쓰고 리뷰하기 위한 규칙입니다. 리뷰에서 스타일 논쟁 대신 이 문서를 가리키면 됩니다. 규칙을 바꾸고 싶으면 이 문서를 고치는 PR을 올립니다.

## 1. 패키지 구조

[Backend 패키지 구조](package-structure.md)를 따릅니다. 도메인 패키지 안은 `controller` / `service` / `domain` / `repository` / `dto`로 나누고, 필요한 것만 만듭니다.

## 2. 이름 규칙

| 대상 | 규칙 | 예 |
|---|---|---|
| Controller | 도메인 + `Controller` | `AuctionController` |
| Service | 도메인 + `Service` | `AuctionService` |
| Repository | 엔티티 + `Repository` | `AuctionRepository` |
| 요청 DTO | 행위·대상 + `Request` | `BidCreateRequest` |
| 응답 DTO | 대상 + `Response` | `AuctionDetailResponse` |
| Enum | 단수 명사 | `AuctionStatus` |
| 테스트 클래스 | 대상 + `Test` | `BidIncrementPolicyTest` |

- 메서드 이름은 동사로 시작합니다. 예: `placeBid`, `findOpenAuctions`
- boolean은 `is` / `has` / `can`으로 시작합니다. 예: `isOpen`, `hasBid`
- 약어도 일반 단어처럼 씁니다. 예: `AutoBid`, `imageUrl` (`URL`, `ID` 대문자 덩어리로 쓰지 않음)
- 상수는 `UPPER_SNAKE_CASE`입니다. 예: `MAX_AMOUNT`

## 3. Controller

- 경로는 [API 명세](../05-api-spec.md)를 그대로 따릅니다. 클래스에 `@RequestMapping("/api/v1/...")`을 붙이고, 자원 이름은 복수형입니다. 예: `/api/v1/auctions/{auctionId}/bids`
- 컨트롤러는 요청을 받아 서비스를 호출하고 응답 DTO를 돌려주는 일만 합니다. 비즈니스 규칙은 서비스·도메인에 둡니다.
- 응답 상태 코드는 명세의 HTTP Status 기준을 따릅니다. 생성은 `201`, 조회·수정·상태 전이는 `200`, 본문 없는 삭제는 `204`입니다.
- 로그인 사용자는 `@AuthenticationPrincipal AuthenticatedUser`로 받는다.
- `AuthenticatedUser.userId()`로 검증된 JWT의 회원 ID를 읽는다.
- 본인 대상 API는 요청 본문·쿼리의 회원 ID 대신 인증 정보의 ID를 사용한다.
- 인증 정보에는 비밀번호나 JPA 엔티티를 넣지 않는다.
- JWT 필터는 토큰을 검증하며, 쓰기 API에서 필요한 ACTIVE 상태 검사는
  해당 서비스에서 수행한다.

```java
@GetMapping("/me")
public UserMeResponse getMe(
    @AuthenticationPrincipal AuthenticatedUser user
) {
    if (user == null) {
        throw new BusinessException(ErrorCode.UNAUTHORIZED);
    }

    return userService.getMe(user.userId());
}
```

## 4. DTO

- DTO는 `record`로 만듭니다.
- 엔티티를 응답으로 직접 반환하지 않고, 응답 DTO로 바꿔서 반환합니다.
- 엔티티 → 응답 DTO 변환은 응답 DTO의 `static from(...)` 메서드에서 합니다.
- 요청 DTO에는 형식 검증 애노테이션을 붙이고, 컨트롤러에서 `@Valid`로 검사합니다 (아래 7. 검증).

```java
public record BidCreateRequest(
        @NotNull @Positive Long amount
) {
}

public record BidResponse(Long id, BidType type, long amount, Instant createdAt) {

    public static BidResponse from(Bid bid) {
        return new BidResponse(bid.getId(), bid.getType(), bid.getAmount(), bid.getCreatedAt());
    }
}
```

## 5. 엔티티

- Lombok은 `@Getter`와 `@NoArgsConstructor(access = AccessLevel.PROTECTED)`까지만 씁니다.
  - `@Setter`, `@Data`는 쓰지 않습니다. 어디서든 값을 바꿀 수 있으면 규칙을 지키는지 추적할 수 없습니다.
  - `@ToString`은 연관 엔티티를 넣으면 서로를 계속 호출하므로 쓰지 않습니다.
- 엔티티에는 `@Builder`를 쓰지 않고, 생성은 의미 있는 이름의 정적 메서드로 합니다. 예: `Auction.create(product, startPrice, startAt, endAt)`. 필수 값을 빼먹지 않게 하고, 생성 시점의 규칙을 한 곳에서 검사하기 위함입니다.
- 상태는 의미 있는 메서드로만 바꿉니다. 예: `auction.cancel(now)`, `trade.proceed(now)`. 규칙에 어긋나면 그 메서드 안에서 `BusinessException`을 던집니다.
- 매핑 규칙
  - id는 `@GeneratedValue(strategy = GenerationType.IDENTITY)`
  - enum은 `@Enumerated(EnumType.STRING)`
  - 시간 컬럼은 `Instant`
  - 연관관계는 `@ManyToOne(fetch = FetchType.LAZY)` 단방향이 기본이며, 양방향은 Product ↔ ProductImage만 허용 ([ERD](erd.md)의 JPA 연관관계 원칙)
- 생성·수정 시각(`createdAt`, `updatedAt`)이 있는 엔티티는 `BaseTimeEntity`(`global/time`)를 상속합니다. 저장·수정할 때 `Clock` 기준 시각이 자동으로 기록되므로 직접 넣지 않습니다.

## 6. 오류 처리

- 비즈니스 규칙 위반은 `throw new BusinessException(ErrorCode.XXX)` 한 가지 방식으로 던집니다.
- `ErrorCode`는 [API 명세](../05-api-spec.md)의 "주요 Error Code" 표와 1:1로 대응합니다. 새 오류가 필요하면 명세 표와 enum을 같은 PR에서 함께 추가합니다.
- 컨트롤러나 서비스에서 try-catch로 잡아 응답을 직접 만들지 않습니다. 전역 예외 처리기가 명세의 공통 Error Response 형식으로 바꿔 줍니다.
- 예상하지 못한 예외는 잡지 않고 그대로 올립니다. 전역 처리기가 500으로 응답하고 로그를 남깁니다.
- `message`는 사용자에게 보여줄 한국어 문장입니다. 프론트는 `message`가 아니라 `code`로 분기합니다.
- 구현은 공통 오류 응답(#19)에서 합니다.

```java
if (!now.isBefore(auction.getEndAt())) {
    throw new BusinessException(ErrorCode.AUCTION_ENDED);
}
```

## 7. 검증

| 종류 | 위치 | 예 | 실패 시 |
|---|---|---|---|
| 형식 검증 | 요청 DTO 애노테이션 + `@Valid` | 빈 값, 길이, 양수 | `400 VALIDATION_ERROR` (자동) |
| 비즈니스 검증 | service / domain | 입찰 가능 시간, 가격 단위, 권한, 상태 전이 | 해당 `ErrorCode` |

- 가격 단위처럼 서비스 정책에 따른 판단은 형식 검증이 아니라 비즈니스 검증입니다 (`INVALID_PRICE_UNIT`).
- 같은 검증을 컨트롤러와 서비스에서 두 번 하지 않습니다.

## 8. 트랜잭션과 락

- `@Transactional`은 service 계층에만 붙입니다.
- 서비스 클래스에 `@Transactional(readOnly = true)`를 붙이고, 데이터를 바꾸는 메서드에만 `@Transactional`을 따로 붙입니다.
- 락을 잡는 순서, 락 전 조회, 격리 수준은 [락 순서와 트랜잭션 규칙](locking.md)을 따릅니다.
- 트랜잭션 안에서 외부 HTTP 호출(Web Push 등)을 하지 않습니다. 커밋 이후 별도 executor에서 보냅니다 ([Realtime 발송 방식](../api/realtime.md#발송-방식)).

## 9. 시간

- 시간 타입은 `Instant`만 씁니다. `LocalDateTime`은 시간대 정보가 없어 쓰지 않습니다.
- 현재 시각은 주입받은 `Clock`으로 구합니다: `Instant.now(clock)`. `Instant.now()`나 `LocalDateTime.now()`를 직접 호출하지 않습니다. 테스트에서 시간을 고정할 수 없기 때문입니다.
- 저장·계산·API는 UTC이고, 한국 시간 변환은 화면(프론트)에서 합니다.

## 10. 테스트

| 종류 | 대상 | 도구 |
|---|---|---|
| 단위 테스트 | 정책 계산, 도메인 메서드 | JUnit 5, AssertJ |
| 통합 테스트 | repository, service, API, 락 | `@SpringBootTest` + Testcontainers MySQL 8.4 |
| 동시성 테스트 | [동시성 테스트 계획](concurrency-testing.md)의 시나리오 | `ExecutorService` + `CountDownLatch` |

- 테스트 메서드 이름은 영어로 짧게 쓰고, `@DisplayName`에 한글 문장으로 설명합니다. 예: `@DisplayName("Bid가 0건이면 시작가로 입찰할 수 있다")`
- 본문은 `// given` / `// when` / `// then` 순서로 씁니다.
- H2를 쓰지 않습니다. MySQL의 락·제약 동작을 검증하지 못합니다.
- 통합 테스트는 `IntegrationTest`(테스트 코드의 `support` 패키지)를 상속합니다. 모든 통합 테스트가 같은 Spring 컨텍스트를 함께 써서 MySQL 컨테이너가 한 번만 뜹니다.
  - 테스트 클래스에서 `@MockitoBean`, `@TestPropertySource` 등으로 설정을 바꾸면 그 클래스만 컨텍스트와 컨테이너를 새로 띄워 느려지므로 꼭 필요할 때만 씁니다.
  - repository 테스트도 `@DataJpaTest` 대신 `IntegrationTest`를 씁니다. `@DataJpaTest`에는 생성·수정 시각 자동 기록 설정이 빠져 있어 저장할 때 NOT NULL 오류가 납니다.
- 시간이 필요한 테스트는 시각을 고정합니다.
  - 통합 테스트: 상속받은 `clock`으로 `clock.fixAt(Instant.parse("2026-10-09T03:00:00Z"))`, `clock.advance(Duration.ofMinutes(10))`. 테스트가 끝나면 실제 시각으로 돌아갑니다.
  - 단위 테스트: `Clock.fixed(...)`를 만들어 넘깁니다.
- 테스트끼리 데이터를 공유하지 않습니다. 각 테스트가 필요한 데이터를 직접 만듭니다.
  - 통합 테스트는 DB를 함께 쓰므로 다른 테스트가 만든 행이 남아 있을 수 있습니다. 전체 개수 대신 자기가 만든 id로 확인합니다.

```java
@Test
@DisplayName("Bid가 0건이면 시작가로 입찰할 수 있다")
void firstBidAtStartPrice() {
    // given
    // when
    // then
}
```

## 11. 포맷

- 저장소 루트의 `.editorconfig`를 따릅니다. Java는 탭 들여쓰기입니다.
- import에 와일드카드(`*`)를 쓰지 않습니다.
- IntelliJ 기본 포매터를 쓰고, 커밋 전에 변경한 파일만 정리합니다 (관련 없는 파일 포맷을 바꾸면 리뷰가 어려워짐).
