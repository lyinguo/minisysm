-- Preserve existing values while allowing fractional rates such as 0.095 (9.5%).
ALTER TABLE sell_info MODIFY COLUMN discount DECIMAL(7,4) NOT NULL DEFAULT 0.0000;
ALTER TABLE sell_info MODIFY COLUMN tax DECIMAL(7,4) NOT NULL DEFAULT 0.0000;
