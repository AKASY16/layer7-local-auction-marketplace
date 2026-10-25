/**
 * 중간 발표 시연용 데이터. demo 프로필로 켤 때만 동작한다 (docs/demo.md).
 *
 * <p>상품·경매를 만드는 service가 아직 없어, 테스트 픽스처(TestFixtures)처럼 상품·경매 엔티티를 EntityManager로 직접 저장한다.
 * 회원은 AuthService, 입찰 기록은 BidService로 만들어 비밀번호 암호화와 입찰 규칙은 실제와 같게 한다.
 * 상품 등록·경매 생성 기능이 생기면 그 service로 바꾼다.
 */
package com.layer7.marketplace.demo;
