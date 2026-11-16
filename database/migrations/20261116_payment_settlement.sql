-- Transaction scopes shared by creation, reviewed revision, import and settlement.
CREATE TABLE IF NOT EXISTS psi_document_write_lock (
  scope VARCHAR(40) NOT NULL PRIMARY KEY
);

-- Proof is produced only by a real atomic cash movement and original-document allocation.
-- Never backfill proof from historical approval flags or reported balances.
CREATE TABLE IF NOT EXISTS psi_payment_posting (
  payment_id VARCHAR(32) NOT NULL PRIMARY KEY,
  fingerprint VARCHAR(64) NOT NULL,
  ledger_fingerprint VARCHAR(64) NOT NULL,
  created_at DATETIME NOT NULL
);
