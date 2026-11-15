-- Explicit catalog only. No history or inferred supplier relationships are imported.
-- The purchase service creates this table automatically when starting.
CREATE TABLE IF NOT EXISTS psi_goods_supplier (
  frame VARCHAR(32) NOT NULL,
  goods VARCHAR(32) NOT NULL,
  supplier VARCHAR(32) NOT NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  `user` VARCHAR(32) NOT NULL,
  updated DATETIME NOT NULL,
  PRIMARY KEY(frame,goods,supplier),
  CONSTRAINT psi_supply_goods FOREIGN KEY(goods) REFERENCES goods(id),
  CONSTRAINT psi_supply_supplier FOREIGN KEY(supplier) REFERENCES supplier(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
