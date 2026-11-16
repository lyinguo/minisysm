-- Preserve stored rates: procurement uses its original percentage convention.
ALTER TABLE bre_info
  MODIFY COLUMN discount DECIMAL(7,4) NOT NULL DEFAULT 0.0000,
  MODIFY COLUMN tax DECIMAL(7,4) NOT NULL DEFAULT 0.0000;

-- No historical approval flag is treated as proof of inventory or financial posting.
CREATE TABLE IF NOT EXISTS psi_purchase_return_posting (
  return_id VARCHAR(32) NOT NULL PRIMARY KEY,
  fingerprint VARCHAR(32) NOT NULL,
  ledger_fingerprint VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL
);
