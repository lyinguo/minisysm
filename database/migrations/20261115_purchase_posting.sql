-- Metadata only. Never reconstruct historical procurement stock/funds from an audit flag.
CREATE TABLE IF NOT EXISTS psi_purchase_posting (purchase_id VARCHAR(32) NOT NULL PRIMARY KEY,fingerprint VARCHAR(32) NOT NULL,created_at DATETIME NOT NULL);
CREATE TABLE IF NOT EXISTS psi_stock_posting_order (sequence BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,movement_id VARCHAR(32) NOT NULL UNIQUE);
