-- Receipt cash and both original-document allocations are committed in one local transaction.
CREATE TABLE IF NOT EXISTS psi_document_write_lock (
  scope VARCHAR(40) NOT NULL PRIMARY KEY
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS psi_receipt_posting (
  receipt_id VARCHAR(32) NOT NULL PRIMARY KEY,
  fingerprint VARCHAR(64) NOT NULL,
  ledger_fingerprint VARCHAR(64) NOT NULL,
  created_at DATETIME NOT NULL
) ENGINE=InnoDB;

-- Keep existing function IDs/role selections, but distinguish create/update/remove.
-- The original catalog used the same URL for create213 and remove216.
-- Only migrate those exact original catalog entries, never reassign role grants.
UPDATE func_perm SET url='/fund/receipt/add'
 WHERE id='213' AND mid='121' AND url='/fund/receipt';
UPDATE func_perm SET url='/fund/receipt/update'
 WHERE id='214' AND mid='121' AND url='/fund/receipt/{id}';
UPDATE func_perm SET url='/fund/receipt/remove'
 WHERE id='216' AND mid='121' AND url='/fund/receipt';
-- Do not create financial proof from historical approval flags.
