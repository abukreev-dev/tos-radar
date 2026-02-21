CREATE TABLE IF NOT EXISTS cabinet_notification_settings (
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    email_digest_enabled TINYINT(1) NOT NULL,
    telegram_digest_enabled TINYINT(1) NOT NULL,
    email_marketing_enabled TINYINT(1) NOT NULL,
    telegram_system_enabled TINYINT(1) NOT NULL,
    email_status VARCHAR(32) NOT NULL,
    telegram_status VARCHAR(32) NOT NULL,
    email_error_code VARCHAR(128) NULL,
    email_error_message TEXT NULL,
    email_error_updated_at VARCHAR(64) NULL,
    telegram_error_code VARCHAR(128) NULL,
    telegram_error_message TEXT NULL,
    telegram_error_updated_at VARCHAR(64) NULL,
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS cabinet_telegram_link_state (
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    pending_code VARCHAR(16) NULL,
    code_expires_at VARCHAR(64) NULL,
    chat_id VARCHAR(128) NULL,
    linked_at VARCHAR(64) NULL,
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS cabinet_telegram_test_send_state (
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    last_sent_at VARCHAR(64) NULL,
    day_key VARCHAR(16) NULL,
    day_count INT NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS cabinet_user_sessions (
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    session_id VARCHAR(128) NOT NULL,
    issued_at VARCHAR(64) NOT NULL,
    revoked_at VARCHAR(64) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (tenant_id, user_id, session_id)
);

CREATE TABLE IF NOT EXISTS cabinet_account_lifecycle (
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    soft_deleted_at VARCHAR(64) NULL,
    purge_at VARCHAR(64) NULL,
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE IF NOT EXISTS cabinet_email_verify_resend_state (
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    last_sent_at VARCHAR(64) NULL,
    day_key VARCHAR(16) NULL,
    day_count INT NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, user_id)
);
