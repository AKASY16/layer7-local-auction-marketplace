-- V1__init_schema.sql
-- MySQL 8.4 / InnoDB / utf8mb4
-- Application time convention: UTC, mapped from Java Instant.
-- Transaction isolation: READ COMMITTED (see docs/backend/locking.md).

CREATE TABLE regions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    region_code VARCHAR(20) NOT NULL,
    sido_name VARCHAR(50) NOT NULL,
    sigungu_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_regions_region_code UNIQUE (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE users (
    id BIGINT NOT NULL AUTO_INCREMENT,
    email VARCHAR(320) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NOT NULL,
    region_id BIGINT NOT NULL,
    trust_score INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_nickname UNIQUE (nickname),
    CONSTRAINT ck_users_status CHECK (status IN ('ACTIVE', 'WITHDRAWN')),
    CONSTRAINT fk_users_region
        FOREIGN KEY (region_id) REFERENCES regions(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE refresh_tokens (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    family_id CHAR(36) NOT NULL,
    token_hash CHAR(64) NOT NULL,
    expires_at DATETIME(6) NOT NULL,
    rotated_at DATETIME(6) NULL,
    revoked_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_refresh_tokens_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    INDEX idx_refresh_tokens_user (user_id),
    INDEX idx_refresh_tokens_family (family_id),
    INDEX idx_refresh_tokens_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE products (
    id BIGINT NOT NULL AUTO_INCREMENT,
    seller_id BIGINT NOT NULL,
    region_id BIGINT NOT NULL,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(120) NOT NULL,
    description TEXT NOT NULL,
    condition_code VARCHAR(30) NOT NULL,
    condition_description VARCHAR(500) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_products_condition CHECK (
        condition_code IN ('UNOPENED', 'LIKE_NEW', 'GOOD', 'FAIR', 'DAMAGED', 'NEEDS_REPAIR')
    ),
    CONSTRAINT ck_products_status CHECK (
        status IN ('ACTIVE', 'SOLD', 'DELETED')
    ),
    CONSTRAINT fk_products_seller
        FOREIGN KEY (seller_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_products_region
        FOREIGN KEY (region_id) REFERENCES regions(id)
        ON DELETE RESTRICT,
    INDEX idx_products_region_status_created (region_id, status, created_at),
    INDEX idx_products_seller_status_created (seller_id, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE product_images (
    id BIGINT NOT NULL AUTO_INCREMENT,
    product_id BIGINT NOT NULL,
    object_key VARCHAR(512) NOT NULL,
    sort_order INT NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_product_images_order UNIQUE (product_id, sort_order),
    CONSTRAINT uq_product_images_object_key UNIQUE (object_key),
    CONSTRAINT ck_product_images_sort_order CHECK (sort_order >= 0),
    CONSTRAINT fk_product_images_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE image_uploads (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    object_key VARCHAR(512) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    size BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_image_uploads_object_key UNIQUE (object_key),
    CONSTRAINT ck_image_uploads_status CHECK (
        status IN ('PENDING', 'ATTACHED', 'DETACHED')
    ),
    CONSTRAINT ck_image_uploads_content_type CHECK (
        content_type IN ('image/jpeg', 'image/png', 'image/webp')
    ),
    CONSTRAINT ck_image_uploads_size CHECK (size > 0),
    CONSTRAINT fk_image_uploads_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    INDEX idx_image_uploads_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE auctions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    product_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    start_price BIGINT NOT NULL,
    current_price BIGINT NOT NULL,
    leading_bid_id BIGINT NULL,
    winning_bid_id BIGINT NULL,
    start_at DATETIME(6) NOT NULL,
    end_at DATETIME(6) NOT NULL,
    relisted_from_auction_id BIGINT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_auctions_leading_bid UNIQUE (leading_bid_id),
    CONSTRAINT uq_auctions_winning_bid UNIQUE (winning_bid_id),
    CONSTRAINT ck_auctions_status CHECK (
        status IN ('READY', 'OPEN', 'ENDED', 'CANCELED')
    ),
    CONSTRAINT ck_auctions_start_price CHECK (start_price >= 100),
    CONSTRAINT ck_auctions_current_price CHECK (current_price >= start_price),
    CONSTRAINT ck_auctions_period CHECK (start_at < end_at),
    CONSTRAINT ck_auctions_relist_not_self CHECK (
        relisted_from_auction_id IS NULL OR relisted_from_auction_id <> id
    ),
    CONSTRAINT fk_auctions_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_auctions_relisted_from
        FOREIGN KEY (relisted_from_auction_id) REFERENCES auctions(id)
        ON DELETE RESTRICT,
    INDEX idx_auctions_status_start (status, start_at),
    INDEX idx_auctions_status_end (status, end_at),
    INDEX idx_auctions_product_status (product_id, status),
    INDEX idx_auctions_product_created (product_id, created_at),
    INDEX idx_auctions_relisted_from (relisted_from_auction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE auto_bids (
    id BIGINT NOT NULL AUTO_INCREMENT,
    auction_id BIGINT NOT NULL,
    bidder_id BIGINT NOT NULL,
    max_amount BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_auto_bids_auction_bidder UNIQUE (auction_id, bidder_id),
    CONSTRAINT ck_auto_bids_max_amount CHECK (max_amount >= 100),
    CONSTRAINT ck_auto_bids_status CHECK (
        status IN ('ACTIVE', 'STOPPED', 'EXHAUSTED')
    ),
    CONSTRAINT fk_auto_bids_auction
        FOREIGN KEY (auction_id) REFERENCES auctions(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_auto_bids_bidder
        FOREIGN KEY (bidder_id) REFERENCES users(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE bids (
    id BIGINT NOT NULL AUTO_INCREMENT,
    auction_id BIGINT NOT NULL,
    bidder_id BIGINT NOT NULL,
    amount BIGINT NOT NULL,
    type VARCHAR(20) NOT NULL,
    auto_bid_id BIGINT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_bids_auction_amount UNIQUE (auction_id, amount),
    CONSTRAINT ck_bids_amount CHECK (amount >= 100),
    CONSTRAINT ck_bids_type CHECK (type IN ('MANUAL', 'AUTO')),
    CONSTRAINT ck_bids_auto_reference CHECK (
        (type = 'MANUAL' AND auto_bid_id IS NULL)
        OR
        (type = 'AUTO' AND auto_bid_id IS NOT NULL)
    ),
    CONSTRAINT fk_bids_auction
        FOREIGN KEY (auction_id) REFERENCES auctions(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_bids_bidder
        FOREIGN KEY (bidder_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_bids_auto_bid
        FOREIGN KEY (auto_bid_id) REFERENCES auto_bids(id)
        ON DELETE RESTRICT,
    INDEX idx_bids_auction_created (auction_id, created_at),
    INDEX idx_bids_bidder_created (bidder_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

ALTER TABLE auctions
    ADD CONSTRAINT fk_auctions_leading_bid
        FOREIGN KEY (leading_bid_id) REFERENCES bids(id)
        ON DELETE RESTRICT,
    ADD CONSTRAINT fk_auctions_winning_bid
        FOREIGN KEY (winning_bid_id) REFERENCES bids(id)
        ON DELETE RESTRICT;

CREATE TABLE product_appends (
    id BIGINT NOT NULL AUTO_INCREMENT,
    auction_id BIGINT NOT NULL,
    content VARCHAR(200) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_product_appends_auction
        FOREIGN KEY (auction_id) REFERENCES auctions(id)
        ON DELETE RESTRICT,
    INDEX idx_product_appends_auction_created (auction_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE trades (
    id BIGINT NOT NULL AUTO_INCREMENT,
    auction_id BIGINT NOT NULL,
    seller_id BIGINT NOT NULL,
    buyer_id BIGINT NOT NULL,
    status VARCHAR(30) NOT NULL,
    response_deadline DATETIME(6) NOT NULL,
    trade_deadline DATETIME(6) NOT NULL,
    completion_requested_by BIGINT NULL,
    completion_requested_at DATETIME(6) NULL,
    completion_deadline DATETIME(6) NULL,
    completed_at DATETIME(6) NULL,
    canceled_by BIGINT NULL,
    canceled_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_trades_auction UNIQUE (auction_id),
    CONSTRAINT ck_trades_status CHECK (
        status IN (
            'AWAITING_RESPONSE',
            'IN_PROGRESS',
            'COMPLETION_REQUESTED',
            'COMPLETED',
            'DECLINED',
            'NO_RESPONSE',
            'CANCELED',
            'EXPIRED'
        )
    ),
    CONSTRAINT ck_trades_parties CHECK (seller_id <> buyer_id),
    CONSTRAINT ck_trades_deadlines CHECK (response_deadline < trade_deadline),
    CONSTRAINT ck_trades_completion_request CHECK (
        (completion_requested_by IS NULL
            AND completion_requested_at IS NULL
            AND completion_deadline IS NULL)
        OR
        (completion_requested_by IS NOT NULL
            AND completion_requested_at IS NOT NULL
            AND completion_deadline IS NOT NULL)
    ),
    CONSTRAINT ck_trades_cancel_pair CHECK (
        (canceled_by IS NULL AND canceled_at IS NULL)
        OR
        (canceled_by IS NOT NULL AND canceled_at IS NOT NULL)
    ),
    CONSTRAINT fk_trades_auction
        FOREIGN KEY (auction_id) REFERENCES auctions(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_trades_seller
        FOREIGN KEY (seller_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_trades_buyer
        FOREIGN KEY (buyer_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_trades_completion_requester
        FOREIGN KEY (completion_requested_by) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_trades_canceled_by
        FOREIGN KEY (canceled_by) REFERENCES users(id)
        ON DELETE RESTRICT,
    INDEX idx_trades_status_deadline (status, response_deadline),
    INDEX idx_trades_status_trade_deadline (status, trade_deadline),
    INDEX idx_trades_status_completion_deadline (status, completion_deadline),
    INDEX idx_trades_seller_created (seller_id, created_at),
    INDEX idx_trades_buyer_created (buyer_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE trust_histories (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    trade_id BIGINT NOT NULL,
    delta INT NOT NULL,
    reason VARCHAR(40) NOT NULL,
    score_after INT NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_trust_histories_effect UNIQUE (trade_id, user_id, reason),
    CONSTRAINT ck_trust_histories_delta CHECK (delta <> 0),
    CONSTRAINT ck_trust_histories_reason CHECK (
        reason IN (
            'TRADE_COMPLETED',
            'WINNER_DECLINED',
            'WINNER_NO_RESPONSE',
            'TRADE_CANCELED'
        )
    ),
    CONSTRAINT fk_trust_histories_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_trust_histories_trade
        FOREIGN KEY (trade_id) REFERENCES trades(id)
        ON DELETE RESTRICT,
    INDEX idx_trust_histories_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE user_restrictions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    type VARCHAR(30) NOT NULL,
    reason VARCHAR(50) NOT NULL,
    source VARCHAR(20) NOT NULL,
    trigger_trade_id BIGINT NULL,
    starts_at DATETIME(6) NOT NULL,
    ends_at DATETIME(6) NULL,
    lifted_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_user_restrictions_trigger_trade UNIQUE (trigger_trade_id),
    CONSTRAINT ck_user_restrictions_type CHECK (type IN ('TRADING')),
    CONSTRAINT ck_user_restrictions_reason CHECK (
        reason IN ('CONSECUTIVE_FAILURES', 'ADMIN_ACTION')
    ),
    CONSTRAINT ck_user_restrictions_source CHECK (source IN ('SYSTEM', 'ADMIN')),
    CONSTRAINT ck_user_restrictions_period CHECK (
        ends_at IS NULL OR starts_at < ends_at
    ),
    CONSTRAINT ck_user_restrictions_system CHECK (
        source <> 'SYSTEM'
        OR (trigger_trade_id IS NOT NULL AND ends_at IS NOT NULL)
    ),
    CONSTRAINT fk_user_restrictions_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_user_restrictions_trigger_trade
        FOREIGN KEY (trigger_trade_id) REFERENCES trades(id)
        ON DELETE RESTRICT,
    INDEX idx_user_restrictions_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE notifications (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    type VARCHAR(50) NOT NULL,
    message VARCHAR(500) NOT NULL,
    product_id BIGINT NULL,
    auction_id BIGINT NULL,
    trade_id BIGINT NULL,
    read_at DATETIME(6) NULL,
    dedupe_key VARCHAR(200) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_notifications_dedupe_key UNIQUE (dedupe_key),
    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_notifications_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_notifications_auction
        FOREIGN KEY (auction_id) REFERENCES auctions(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_notifications_trade
        FOREIGN KEY (trade_id) REFERENCES trades(id)
        ON DELETE RESTRICT,
    INDEX idx_notifications_user_read_created (user_id, read_at, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE push_subscriptions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    endpoint TEXT NOT NULL,
    endpoint_hash CHAR(64) NOT NULL,
    p256dh VARCHAR(255) NOT NULL,
    auth VARCHAR(255) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_push_subscriptions_endpoint_hash UNIQUE (endpoint_hash),
    CONSTRAINT fk_push_subscriptions_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    INDEX idx_push_subscriptions_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE favorites (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_favorites_user_product UNIQUE (user_id, product_id),
    CONSTRAINT fk_favorites_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_favorites_product
        FOREIGN KEY (product_id) REFERENCES products(id)
        ON DELETE RESTRICT,
    INDEX idx_favorites_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE idempotency_requests (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    scope VARCHAR(50) NOT NULL,
    idempotency_key VARCHAR(100) NOT NULL,
    request_hash CHAR(64) NOT NULL,
    resource_type VARCHAR(40) NULL,
    resource_id BIGINT NULL,
    response_status SMALLINT NULL,
    response_body JSON NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_idempotency_user_scope_key
        UNIQUE (user_id, scope, idempotency_key),
    CONSTRAINT ck_idempotency_resource_pair CHECK (
        (resource_type IS NULL AND resource_id IS NULL)
        OR
        (resource_type IS NOT NULL AND resource_id IS NOT NULL)
    ),
    CONSTRAINT fk_idempotency_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT,
    INDEX idx_idempotency_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
