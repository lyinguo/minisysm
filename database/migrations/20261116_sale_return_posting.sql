-- Return posting proof. No historical approved return is auto-posted or backfilled.
-- The application creates the same table on startup for fresh installations.
CREATE TABLE IF NOT EXISTS psi_sale_return_posting (
    return_id VARCHAR(32) NOT NULL PRIMARY KEY,
    fingerprint VARCHAR(32) NOT NULL,
    ledger_fingerprint VARCHAR(32) NOT NULL,
    created_at DATETIME NOT NULL
);
