-- Cross-service integrity guards. No business rows are deleted or rewritten.

-- Empty/0 optional legacy references are tolerated. New nonempty IDs must exist.

-- Install during maintenance; DDL is not transactional. Use master-integrity.py.

DELIMITER $$

DROP PROCEDURE IF EXISTS psi_install_parent_refs$$

CREATE PROCEDURE psi_install_parent_refs() BEGIN
IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='frame' AND column_name='psi_parent_id') THEN
ALTER TABLE frame ADD COLUMN psi_parent_id VARCHAR(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci GENERATED ALWAYS AS (NULLIF(NULLIF(pid,'0'),'')) STORED;
END IF;
IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='psi_frame_parent_fk') THEN
ALTER TABLE frame ADD CONSTRAINT psi_frame_parent_fk FOREIGN KEY(psi_parent_id) REFERENCES frame(id) ON DELETE RESTRICT ON UPDATE RESTRICT;
END IF;
IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='menu' AND column_name='psi_parent_id') THEN
ALTER TABLE menu ADD COLUMN psi_parent_id VARCHAR(32) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci GENERATED ALWAYS AS (NULLIF(NULLIF(pid,'0'),'')) STORED;
END IF;
IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND constraint_name='psi_menu_parent_fk') THEN
ALTER TABLE menu ADD CONSTRAINT psi_menu_parent_fk FOREIGN KEY(psi_parent_id) REFERENCES menu(id) ON DELETE RESTRICT ON UPDATE RESTRICT;
END IF;
END$$

SET @psi_previous_fk_checks=@@FOREIGN_KEY_CHECKS$$

SET SESSION FOREIGN_KEY_CHECKS=0$$

CALL psi_install_parent_refs()$$

SET SESSION FOREIGN_KEY_CHECKS=@psi_previous_fk_checks$$

DROP PROCEDURE psi_install_parent_refs$$

DROP TRIGGER IF EXISTS `psi_guard_del_annex`$$

CREATE TRIGGER `psi_guard_del_annex` BEFORE DELETE ON `annex` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `user` WHERE `img`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:annex:user'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_annex`$$

CREATE TRIGGER `psi_guard_id_annex` BEFORE UPDATE ON `annex` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:annex'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_customer`$$

CREATE TRIGGER `psi_guard_del_customer` BEFORE DELETE ON `customer` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
IF COALESCE(OLD.balance,0) <> 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:balance:customer'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bill` WHERE `customer`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:customer:bill'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `extry` WHERE `customer`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:customer:extry'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `ice` WHERE `customer`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:customer:ice'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `imy` WHERE `customer`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:customer:imy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sell` WHERE `customer`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:customer:sell'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sor` WHERE `customer`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:customer:sor'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sre` WHERE `customer`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:customer:sre'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_customer`$$

CREATE TRIGGER `psi_guard_id_customer` BEFORE UPDATE ON `customer` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:customer'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_supplier`$$

CREATE TRIGGER `psi_guard_del_supplier` BEFORE DELETE ON `supplier` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
IF COALESCE(OLD.balance,0) <> 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:balance:supplier'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bill` WHERE `supplier`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:supplier:bill'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bor` WHERE `supplier`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:supplier:bor'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bre` WHERE `supplier`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:supplier:bre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `buy` WHERE `supplier`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:supplier:buy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `entry` WHERE `supplier`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:supplier:entry'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `oce` WHERE `supplier`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:supplier:oce'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `omy` WHERE `supplier`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:supplier:omy'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_supplier`$$

CREATE TRIGGER `psi_guard_id_supplier` BEFORE UPDATE ON `supplier` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:supplier'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_goods`$$

CREATE TRIGGER `psi_guard_del_goods` BEFORE DELETE ON `goods` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `batch` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:batch'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bor_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:bor_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bre_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:bre_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `buy_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:buy_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `entry_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:entry_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `extry_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:extry_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `room` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:room'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sell_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:sell_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `serial` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:serial'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `serve` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:serve'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sor_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:sor_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sre_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:sre_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `summary` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:summary'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `swap_info` WHERE `goods`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:swap_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `attr` WHERE `pid`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:goods:attr'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_goods`$$

CREATE TRIGGER `psi_guard_id_goods` BEFORE UPDATE ON `goods` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:goods'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_warehouse`$$

CREATE TRIGGER `psi_guard_del_warehouse` BEFORE DELETE ON `warehouse` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `batch` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:batch'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bor_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:bor_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bre_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:bre_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `buy_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:buy_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `entry_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:entry_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `extry_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:extry_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `room` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:room'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sell_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:sell_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `serial` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:serial'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sor_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:sor_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sre_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:sre_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `summary` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:summary'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `swap_info` WHERE `warehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:swap_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `swap_info` WHERE `storehouse`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:warehouse:swap_info'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_warehouse`$$

CREATE TRIGGER `psi_guard_id_warehouse` BEFORE UPDATE ON `warehouse` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:warehouse'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_account`$$

CREATE TRIGGER `psi_guard_del_account` BEFORE DELETE ON `account` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
IF COALESCE(OLD.balance,0) <> 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:balance:account'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `allot_info` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:allot_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bre` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:bre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `buy` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:buy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `ice` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:ice'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `imy_info` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:imy_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `oce` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:oce'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `omy_info` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:omy_info'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sell` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:sell'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sre` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:sre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `account_info` WHERE `pid`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:account:account_info'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_account`$$

CREATE TRIGGER `psi_guard_id_account` BEFORE UPDATE ON `account` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:account'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_dict_type`$$

CREATE TRIGGER `psi_guard_del_dict_type` BEFORE DELETE ON `dict_type` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `dict` WHERE `tid`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:dict_type:dict'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_dict_type`$$

CREATE TRIGGER `psi_guard_id_dict_type` BEFORE UPDATE ON `dict_type` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:dict_type'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_menu`$$

CREATE TRIGGER `psi_guard_del_menu` BEFORE DELETE ON `menu` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
SELECT id INTO hit_id FROM role WHERE JSON_CONTAINS_PATH(IF(JSON_VALID(root),root,'{}'),'one',CONCAT('$.',JSON_QUOTE(OLD.id))) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:menu:role'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `menu` WHERE `pid`=OLD.id LIMIT 1;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:menu:menu'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `func_perm` WHERE `mid`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:menu:func_perm'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_menu`$$

CREATE TRIGGER `psi_guard_id_menu` BEFORE UPDATE ON `menu` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:menu'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_role`$$

CREATE TRIGGER `psi_guard_del_role` BEFORE DELETE ON `role` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `user` WHERE `role`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:role:user'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_role`$$

CREATE TRIGGER `psi_guard_id_role` BEFORE UPDATE ON `role` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:role'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_people`$$

CREATE TRIGGER `psi_guard_del_people` BEFORE DELETE ON `people` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `allot` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:allot'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bill` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:bill'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bor` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:bor'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bre` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:bre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `buy` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:buy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `entry` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:entry'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `extry` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:extry'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `ice` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:ice'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `imy` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:imy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `oce` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:oce'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `omy` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:omy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sell` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:sell'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sor` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:sor'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sre` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:sre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `swap` WHERE `people`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:people:swap'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_people`$$

CREATE TRIGGER `psi_guard_id_people` BEFORE UPDATE ON `people` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:people'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_frame`$$

CREATE TRIGGER `psi_guard_del_frame` BEFORE DELETE ON `frame` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `account` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:account'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `allot` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:allot'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bill` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:bill'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bor` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:bor'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bre` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:bre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `buy` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:buy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `customer` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:customer'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `entry` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:entry'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `extry` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:extry'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `ice` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:ice'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `imy` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:imy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `oce` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:oce'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `omy` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:omy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `people` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:people'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sell` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:sell'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sor` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:sor'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sre` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:sre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `supplier` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:supplier'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `swap` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:swap'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `user` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:user'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `warehouse` WHERE `frame`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:warehouse'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `frame` WHERE `pid`=OLD.id LIMIT 1;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:frame:frame'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_frame`$$

CREATE TRIGGER `psi_guard_id_frame` BEFORE UPDATE ON `frame` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:frame'; END IF;  END$$

DROP TRIGGER IF EXISTS `psi_guard_del_user`$$

CREATE TRIGGER `psi_guard_del_user` BEFORE DELETE ON `user` FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;
IF OLD.`user`='admin' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:reserved:user'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `allot` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:allot'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bill` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:bill'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bor` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:bor'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `bre` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:bre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `buy` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:buy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `customer` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:customer'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `entry` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:entry'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `extry` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:extry'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `ice` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:ice'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `imy` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:imy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `log` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:log'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `oce` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:oce'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `often` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:often'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `omy` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:omy'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `period` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:period'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `record` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:record'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sell` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:sell'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sor` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:sor'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `sre` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:sre'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `supplier` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:supplier'; END IF;
SET hit_id = NULL;
SELECT id INTO hit_id FROM `swap` WHERE `user`=OLD.id OR (OLD.`user` NOT IN ('','0') AND `user`=OLD.`user`) LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:user:swap'; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_id_user`$$

CREATE TRIGGER `psi_guard_id_user` BEFORE UPDATE ON `user` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:user'; END IF; IF NOT (NEW.`user` <=> OLD.`user`) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:login:user'; END IF; END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_user`$$

CREATE TRIGGER `psi_guard_insert_user` BEFORE INSERT ON `user` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`img` IS NOT NULL AND NEW.`img` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `annex` WHERE id=NEW.`img` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:annex'; END IF; END IF;
IF NEW.`role` IS NOT NULL AND NEW.`role` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `role` WHERE id=NEW.`role` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:role'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_user`$$

CREATE TRIGGER `psi_guard_update_user` BEFORE UPDATE ON `user` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`img` <=> OLD.`img`) AND NEW.`img` IS NOT NULL AND NEW.`img` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `annex` WHERE id=NEW.`img` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:annex'; END IF; END IF;
IF NOT (NEW.`role` <=> OLD.`role`) AND NEW.`role` IS NOT NULL AND NEW.`role` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `role` WHERE id=NEW.`role` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:role'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_bill`$$

CREATE TRIGGER `psi_guard_insert_bill` BEFORE INSERT ON `bill` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_bill`$$

CREATE TRIGGER `psi_guard_update_bill` BEFORE UPDATE ON `bill` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`customer` <=> OLD.`customer`) AND NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NOT (NEW.`supplier` <=> OLD.`supplier`) AND NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_extry`$$

CREATE TRIGGER `psi_guard_insert_extry` BEFORE INSERT ON `extry` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_extry`$$

CREATE TRIGGER `psi_guard_update_extry` BEFORE UPDATE ON `extry` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`customer` <=> OLD.`customer`) AND NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_ice`$$

CREATE TRIGGER `psi_guard_insert_ice` BEFORE INSERT ON `ice` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_ice`$$

CREATE TRIGGER `psi_guard_update_ice` BEFORE UPDATE ON `ice` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`customer` <=> OLD.`customer`) AND NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_imy`$$

CREATE TRIGGER `psi_guard_insert_imy` BEFORE INSERT ON `imy` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_imy`$$

CREATE TRIGGER `psi_guard_update_imy` BEFORE UPDATE ON `imy` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`customer` <=> OLD.`customer`) AND NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_sell`$$

CREATE TRIGGER `psi_guard_insert_sell` BEFORE INSERT ON `sell` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_sell`$$

CREATE TRIGGER `psi_guard_update_sell` BEFORE UPDATE ON `sell` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`customer` <=> OLD.`customer`) AND NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_sor`$$

CREATE TRIGGER `psi_guard_insert_sor` BEFORE INSERT ON `sor` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_sor`$$

CREATE TRIGGER `psi_guard_update_sor` BEFORE UPDATE ON `sor` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`customer` <=> OLD.`customer`) AND NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_sre`$$

CREATE TRIGGER `psi_guard_insert_sre` BEFORE INSERT ON `sre` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_sre`$$

CREATE TRIGGER `psi_guard_update_sre` BEFORE UPDATE ON `sre` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`customer` <=> OLD.`customer`) AND NEW.`customer` IS NOT NULL AND NEW.`customer` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `customer` WHERE id=NEW.`customer` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:customer'; END IF; END IF;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_bor`$$

CREATE TRIGGER `psi_guard_insert_bor` BEFORE INSERT ON `bor` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_bor`$$

CREATE TRIGGER `psi_guard_update_bor` BEFORE UPDATE ON `bor` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`supplier` <=> OLD.`supplier`) AND NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_bre`$$

CREATE TRIGGER `psi_guard_insert_bre` BEFORE INSERT ON `bre` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_bre`$$

CREATE TRIGGER `psi_guard_update_bre` BEFORE UPDATE ON `bre` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`supplier` <=> OLD.`supplier`) AND NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_buy`$$

CREATE TRIGGER `psi_guard_insert_buy` BEFORE INSERT ON `buy` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_buy`$$

CREATE TRIGGER `psi_guard_update_buy` BEFORE UPDATE ON `buy` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`supplier` <=> OLD.`supplier`) AND NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_entry`$$

CREATE TRIGGER `psi_guard_insert_entry` BEFORE INSERT ON `entry` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_entry`$$

CREATE TRIGGER `psi_guard_update_entry` BEFORE UPDATE ON `entry` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`supplier` <=> OLD.`supplier`) AND NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_oce`$$

CREATE TRIGGER `psi_guard_insert_oce` BEFORE INSERT ON `oce` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_oce`$$

CREATE TRIGGER `psi_guard_update_oce` BEFORE UPDATE ON `oce` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`supplier` <=> OLD.`supplier`) AND NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_omy`$$

CREATE TRIGGER `psi_guard_insert_omy` BEFORE INSERT ON `omy` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_omy`$$

CREATE TRIGGER `psi_guard_update_omy` BEFORE UPDATE ON `omy` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`supplier` <=> OLD.`supplier`) AND NEW.`supplier` IS NOT NULL AND NEW.`supplier` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `supplier` WHERE id=NEW.`supplier` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:supplier'; END IF; END IF;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_batch`$$

CREATE TRIGGER `psi_guard_insert_batch` BEFORE INSERT ON `batch` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_batch`$$

CREATE TRIGGER `psi_guard_update_batch` BEFORE UPDATE ON `batch` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_bor_info`$$

CREATE TRIGGER `psi_guard_insert_bor_info` BEFORE INSERT ON `bor_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_bor_info`$$

CREATE TRIGGER `psi_guard_update_bor_info` BEFORE UPDATE ON `bor_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_bre_info`$$

CREATE TRIGGER `psi_guard_insert_bre_info` BEFORE INSERT ON `bre_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_bre_info`$$

CREATE TRIGGER `psi_guard_update_bre_info` BEFORE UPDATE ON `bre_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_buy_info`$$

CREATE TRIGGER `psi_guard_insert_buy_info` BEFORE INSERT ON `buy_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_buy_info`$$

CREATE TRIGGER `psi_guard_update_buy_info` BEFORE UPDATE ON `buy_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_entry_info`$$

CREATE TRIGGER `psi_guard_insert_entry_info` BEFORE INSERT ON `entry_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_entry_info`$$

CREATE TRIGGER `psi_guard_update_entry_info` BEFORE UPDATE ON `entry_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_extry_info`$$

CREATE TRIGGER `psi_guard_insert_extry_info` BEFORE INSERT ON `extry_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_extry_info`$$

CREATE TRIGGER `psi_guard_update_extry_info` BEFORE UPDATE ON `extry_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_room`$$

CREATE TRIGGER `psi_guard_insert_room` BEFORE INSERT ON `room` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_room`$$

CREATE TRIGGER `psi_guard_update_room` BEFORE UPDATE ON `room` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_sell_info`$$

CREATE TRIGGER `psi_guard_insert_sell_info` BEFORE INSERT ON `sell_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_sell_info`$$

CREATE TRIGGER `psi_guard_update_sell_info` BEFORE UPDATE ON `sell_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_serial`$$

CREATE TRIGGER `psi_guard_insert_serial` BEFORE INSERT ON `serial` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_serial`$$

CREATE TRIGGER `psi_guard_update_serial` BEFORE UPDATE ON `serial` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_serve`$$

CREATE TRIGGER `psi_guard_insert_serve` BEFORE INSERT ON `serve` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_serve`$$

CREATE TRIGGER `psi_guard_update_serve` BEFORE UPDATE ON `serve` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_sor_info`$$

CREATE TRIGGER `psi_guard_insert_sor_info` BEFORE INSERT ON `sor_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_sor_info`$$

CREATE TRIGGER `psi_guard_update_sor_info` BEFORE UPDATE ON `sor_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_sre_info`$$

CREATE TRIGGER `psi_guard_insert_sre_info` BEFORE INSERT ON `sre_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_sre_info`$$

CREATE TRIGGER `psi_guard_update_sre_info` BEFORE UPDATE ON `sre_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_summary`$$

CREATE TRIGGER `psi_guard_insert_summary` BEFORE INSERT ON `summary` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_summary`$$

CREATE TRIGGER `psi_guard_update_summary` BEFORE UPDATE ON `summary` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_swap_info`$$

CREATE TRIGGER `psi_guard_insert_swap_info` BEFORE INSERT ON `swap_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
IF NEW.`storehouse` IS NOT NULL AND NEW.`storehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`storehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_swap_info`$$

CREATE TRIGGER `psi_guard_update_swap_info` BEFORE UPDATE ON `swap_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`goods` <=> OLD.`goods`) AND NEW.`goods` IS NOT NULL AND NEW.`goods` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`goods` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
IF NOT (NEW.`warehouse` <=> OLD.`warehouse`) AND NEW.`warehouse` IS NOT NULL AND NEW.`warehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`warehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
IF NOT (NEW.`storehouse` <=> OLD.`storehouse`) AND NEW.`storehouse` IS NOT NULL AND NEW.`storehouse` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `warehouse` WHERE id=NEW.`storehouse` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:warehouse'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_attr`$$

CREATE TRIGGER `psi_guard_insert_attr` BEFORE INSERT ON `attr` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`pid` IS NOT NULL AND NEW.`pid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`pid` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_attr`$$

CREATE TRIGGER `psi_guard_update_attr` BEFORE UPDATE ON `attr` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`pid` <=> OLD.`pid`) AND NEW.`pid` IS NOT NULL AND NEW.`pid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `goods` WHERE id=NEW.`pid` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:goods'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_allot_info`$$

CREATE TRIGGER `psi_guard_insert_allot_info` BEFORE INSERT ON `allot_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_allot_info`$$

CREATE TRIGGER `psi_guard_update_allot_info` BEFORE UPDATE ON `allot_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_imy_info`$$

CREATE TRIGGER `psi_guard_insert_imy_info` BEFORE INSERT ON `imy_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_imy_info`$$

CREATE TRIGGER `psi_guard_update_imy_info` BEFORE UPDATE ON `imy_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_omy_info`$$

CREATE TRIGGER `psi_guard_insert_omy_info` BEFORE INSERT ON `omy_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_omy_info`$$

CREATE TRIGGER `psi_guard_update_omy_info` BEFORE UPDATE ON `omy_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`account` <=> OLD.`account`) AND NEW.`account` IS NOT NULL AND NEW.`account` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`account` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_account_info`$$

CREATE TRIGGER `psi_guard_insert_account_info` BEFORE INSERT ON `account_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`pid` IS NOT NULL AND NEW.`pid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`pid` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_account_info`$$

CREATE TRIGGER `psi_guard_update_account_info` BEFORE UPDATE ON `account_info` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`pid` <=> OLD.`pid`) AND NEW.`pid` IS NOT NULL AND NEW.`pid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `account` WHERE id=NEW.`pid` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:account'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_dict`$$

CREATE TRIGGER `psi_guard_insert_dict` BEFORE INSERT ON `dict` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`tid` IS NOT NULL AND NEW.`tid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `dict_type` WHERE id=NEW.`tid` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:dict_type'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_dict`$$

CREATE TRIGGER `psi_guard_update_dict` BEFORE UPDATE ON `dict` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`tid` <=> OLD.`tid`) AND NEW.`tid` IS NOT NULL AND NEW.`tid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `dict_type` WHERE id=NEW.`tid` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:dict_type'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_menu`$$

CREATE TRIGGER `psi_guard_insert_menu` BEFORE INSERT ON `menu` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
SET ancestor_id=NEW.`pid`; SET depth=0;
WHILE ancestor_id IS NOT NULL AND ancestor_id NOT IN ('','0') AND depth < 1000 DO
IF ancestor_id=NEW.id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:menu'; END IF;
SET parent_id=NULL; SELECT `pid` INTO parent_id FROM `menu` WHERE id=ancestor_id;
SET ancestor_id=parent_id; SET depth=depth+1; END WHILE;
IF depth >= 1000 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:menu'; END IF;
IF NEW.`pid` IS NOT NULL AND NEW.`pid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `menu` WHERE id=NEW.`pid` LIMIT 1;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:menu'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_menu`$$

CREATE TRIGGER `psi_guard_update_menu` BEFORE UPDATE ON `menu` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
SET ancestor_id=NEW.`pid`; SET depth=0;
WHILE ancestor_id IS NOT NULL AND ancestor_id NOT IN ('','0') AND depth < 1000 DO
IF ancestor_id=NEW.id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:menu'; END IF;
SET parent_id=NULL; SELECT `pid` INTO parent_id FROM `menu` WHERE id=ancestor_id;
SET ancestor_id=parent_id; SET depth=depth+1; END WHILE;
IF depth >= 1000 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:menu'; END IF;
IF NOT (NEW.`pid` <=> OLD.`pid`) AND NEW.`pid` IS NOT NULL AND NEW.`pid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `menu` WHERE id=NEW.`pid` LIMIT 1;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:menu'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_func_perm`$$

CREATE TRIGGER `psi_guard_insert_func_perm` BEFORE INSERT ON `func_perm` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`mid` IS NOT NULL AND NEW.`mid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `menu` WHERE id=NEW.`mid` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:menu'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_func_perm`$$

CREATE TRIGGER `psi_guard_update_func_perm` BEFORE UPDATE ON `func_perm` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`mid` <=> OLD.`mid`) AND NEW.`mid` IS NOT NULL AND NEW.`mid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `menu` WHERE id=NEW.`mid` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:menu'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_allot`$$

CREATE TRIGGER `psi_guard_insert_allot` BEFORE INSERT ON `allot` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_allot`$$

CREATE TRIGGER `psi_guard_update_allot` BEFORE UPDATE ON `allot` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_swap`$$

CREATE TRIGGER `psi_guard_insert_swap` BEFORE INSERT ON `swap` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_swap`$$

CREATE TRIGGER `psi_guard_update_swap` BEFORE UPDATE ON `swap` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`people` <=> OLD.`people`) AND NEW.`people` IS NOT NULL AND NEW.`people` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `people` WHERE id=NEW.`people` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:people'; END IF; END IF;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_account`$$

CREATE TRIGGER `psi_guard_insert_account` BEFORE INSERT ON `account` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_account`$$

CREATE TRIGGER `psi_guard_update_account` BEFORE UPDATE ON `account` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_customer`$$

CREATE TRIGGER `psi_guard_insert_customer` BEFORE INSERT ON `customer` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_customer`$$

CREATE TRIGGER `psi_guard_update_customer` BEFORE UPDATE ON `customer` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_people`$$

CREATE TRIGGER `psi_guard_insert_people` BEFORE INSERT ON `people` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_people`$$

CREATE TRIGGER `psi_guard_update_people` BEFORE UPDATE ON `people` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_supplier`$$

CREATE TRIGGER `psi_guard_insert_supplier` BEFORE INSERT ON `supplier` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_supplier`$$

CREATE TRIGGER `psi_guard_update_supplier` BEFORE UPDATE ON `supplier` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_warehouse`$$

CREATE TRIGGER `psi_guard_insert_warehouse` BEFORE INSERT ON `warehouse` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_warehouse`$$

CREATE TRIGGER `psi_guard_update_warehouse` BEFORE UPDATE ON `warehouse` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`frame` <=> OLD.`frame`) AND NEW.`frame` IS NOT NULL AND NEW.`frame` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`frame` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_frame`$$

CREATE TRIGGER `psi_guard_insert_frame` BEFORE INSERT ON `frame` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
SET ancestor_id=NEW.`pid`; SET depth=0;
WHILE ancestor_id IS NOT NULL AND ancestor_id NOT IN ('','0') AND depth < 1000 DO
IF ancestor_id=NEW.id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:frame'; END IF;
SET parent_id=NULL; SELECT `pid` INTO parent_id FROM `frame` WHERE id=ancestor_id;
SET ancestor_id=parent_id; SET depth=depth+1; END WHILE;
IF depth >= 1000 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:frame'; END IF;
IF NEW.`pid` IS NOT NULL AND NEW.`pid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`pid` LIMIT 1;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_frame`$$

CREATE TRIGGER `psi_guard_update_frame` BEFORE UPDATE ON `frame` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
SET ancestor_id=NEW.`pid`; SET depth=0;
WHILE ancestor_id IS NOT NULL AND ancestor_id NOT IN ('','0') AND depth < 1000 DO
IF ancestor_id=NEW.id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:frame'; END IF;
SET parent_id=NULL; SELECT `pid` INTO parent_id FROM `frame` WHERE id=ancestor_id;
SET ancestor_id=parent_id; SET depth=depth+1; END WHILE;
IF depth >= 1000 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:frame'; END IF;
IF NOT (NEW.`pid` <=> OLD.`pid`) AND NEW.`pid` IS NOT NULL AND NEW.`pid` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `frame` WHERE id=NEW.`pid` LIMIT 1;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:frame'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_log`$$

CREATE TRIGGER `psi_guard_insert_log` BEFORE INSERT ON `log` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_log`$$

CREATE TRIGGER `psi_guard_update_log` BEFORE UPDATE ON `log` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_often`$$

CREATE TRIGGER `psi_guard_insert_often` BEFORE INSERT ON `often` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_often`$$

CREATE TRIGGER `psi_guard_update_often` BEFORE UPDATE ON `often` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_period`$$

CREATE TRIGGER `psi_guard_insert_period` BEFORE INSERT ON `period` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_period`$$

CREATE TRIGGER `psi_guard_update_period` BEFORE UPDATE ON `period` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_insert_record`$$

CREATE TRIGGER `psi_guard_insert_record` BEFORE INSERT ON `record` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_update_record`$$

CREATE TRIGGER `psi_guard_update_record` BEFORE UPDATE ON `record` FOR EACH ROW BEGIN
DECLARE parent_id VARCHAR(32) DEFAULT NULL;
DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;
DECLARE depth INT DEFAULT 0;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;
IF NOT (NEW.`user` <=> OLD.`user`) AND NEW.`user` IS NOT NULL AND NEW.`user` NOT IN ('','0') THEN
SET parent_id = NULL;
SELECT id INTO parent_id FROM `user` WHERE id=NEW.`user` OR `user`=NEW.`user` LIMIT 1 LOCK IN SHARE MODE;
IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:user'; END IF; END IF;
END$$

DROP TRIGGER IF EXISTS `psi_guard_fun_update`$$

CREATE TRIGGER `psi_guard_fun_update` BEFORE UPDATE ON sys FOR EACH ROW BEGIN IF OLD.name='fun' AND (NOT (NEW.info <=> OLD.info) OR NOT (NEW.name <=> OLD.name)) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:readonly:sys'; END IF; END$$

DROP TRIGGER IF EXISTS `psi_guard_fun_delete`$$

CREATE TRIGGER `psi_guard_fun_delete` BEFORE DELETE ON sys FOR EACH ROW BEGIN IF OLD.name='fun' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:readonly:sys'; END IF; END$$

DROP TRIGGER IF EXISTS psi_guard_initial_account$$

CREATE TRIGGER psi_guard_initial_account BEFORE UPDATE ON account FOR EACH ROW BEGIN
DECLARE hit_id VARCHAR(32) DEFAULT NULL;
DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id=NULL;
IF NOT (NEW.initial <=> OLD.initial) THEN
SET hit_id=NULL;
SELECT id INTO hit_id FROM `allot_info` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `bre` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `buy` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `ice` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `imy_info` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `oce` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `omy_info` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `sell` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `sre` WHERE `account`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
SET hit_id=NULL;
SELECT id INTO hit_id FROM `account_info` WHERE `pid`=OLD.id LIMIT 1 FOR UPDATE;
IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;
END IF;
END$$
DELIMITER ;
