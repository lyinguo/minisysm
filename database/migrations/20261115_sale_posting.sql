-- Posting metadata only. Does not invent movements for historically audited sales.
CREATE TABLE IF NOT EXISTS psi_sale_posting (sale_id VARCHAR(32) NOT NULL PRIMARY KEY,fingerprint VARCHAR(32) NOT NULL,created_at DATETIME NOT NULL);
CREATE TABLE IF NOT EXISTS psi_stock_posting_order (sequence BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,movement_id VARCHAR(32) NOT NULL UNIQUE);
