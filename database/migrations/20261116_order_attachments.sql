-- Procurement ORDER attachments. The purchase service also creates this table on startup.
-- No public URL or business data is included. Legacy bor.file values are not migrated.
-- Removed files remain for audit while the order exists. An allowed unused-draft
-- physical deletion cascades active/removed binaries; independent operation history survives.
CREATE TABLE IF NOT EXISTS psi_bor_attachment (
  id VARCHAR(32) NOT NULL PRIMARY KEY,
  order_id VARCHAR(32) NOT NULL,
  name VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  file_size INT NOT NULL,
  sha256 CHAR(64) NOT NULL,
  body MEDIUMBLOB NOT NULL,
  created_at DATETIME NOT NULL,
  user_id VARCHAR(32) NOT NULL,
  removed_at DATETIME NULL,
  removed_by VARCHAR(32) NULL,
  INDEX(order_id),
  CONSTRAINT fk_bor_attachment_order FOREIGN KEY(order_id) REFERENCES bor(id) ON DELETE CASCADE,
  CONSTRAINT fk_bor_attachment_user FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;
