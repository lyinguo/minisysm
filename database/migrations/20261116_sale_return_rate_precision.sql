-- Preserve existing values; do not reinterpret historical percentage conventions.
-- New source-bound return drafts use the source sales fraction (0.13 means 13%).
ALTER TABLE sre_info
  MODIFY COLUMN discount DECIMAL(7,4) NOT NULL DEFAULT 0.0000,
  MODIFY COLUMN tax DECIMAL(7,4) NOT NULL DEFAULT 0.0000;
