-- 테스트 전용 테이블. src/test에만 있어서 운영 DB에는 적용되지 않는다.
-- BaseTimeEntity의 생성·수정 시각이 실제 MySQL DATETIME(6) 컬럼에 Clock 기준 UTC로 저장되는지 확인한다 (BaseTimeEntityTest).
CREATE TABLE test_audited_samples (
    id BIGINT NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
