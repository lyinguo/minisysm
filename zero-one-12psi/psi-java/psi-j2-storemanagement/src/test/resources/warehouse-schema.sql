CREATE TABLE `frame` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NULL DEFAULT NULL,
  `name` varchar(32) NOT NULL,
  `sort` int NULL DEFAULT 0,
  `data` varchar(256) NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `warehouse` (
  `id` varchar(32) NOT NULL,
  `name` varchar(32) NOT NULL,
  `number` varchar(32) NOT NULL,
  `frame` varchar(32) NOT NULL DEFAULT '0',
  `contacts` varchar(32) NULL DEFAULT NULL,
  `tel` varchar(32) NULL DEFAULT NULL,
  `add` varchar(64) NULL DEFAULT NULL,
  `data` varchar(256) NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `goods` (
  `id` varchar(32) NOT NULL,
  `name` varchar(32) NOT NULL,
  `py` varchar(32) NOT NULL,
  `number` varchar(32) NOT NULL,
  `spec` varchar(32) NULL DEFAULT NULL,
  `category` varchar(32) NOT NULL,
  `brand` varchar(32) NULL DEFAULT NULL,
  `unit` varchar(32) NOT NULL,
  `buy` decimal(12, 4) NOT NULL,
  `sell` decimal(12, 4) NOT NULL,
  `code` varchar(64) NULL DEFAULT NULL,
  `location` varchar(64) NULL DEFAULT NULL,
  `stock` decimal(12, 4) NOT NULL,
  `type` tinyint(1) NOT NULL,
  `data` varchar(256) NULL DEFAULT NULL,
  `imgs` text NULL,
  `details` text NULL,
  `units` text NULL,
  `strategy` text NULL,
  `serial` tinyint(1) NULL DEFAULT 0,
  `batch` tinyint(1) NULL DEFAULT 0,
  `validity` tinyint(1) NULL DEFAULT 0,
  `protect` smallint NULL DEFAULT 0,
  `threshold` smallint NULL DEFAULT 0,
  `more` text NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `entry` (
  `id` varchar(32) NOT NULL,
  `supplier` varchar(32) NOT NULL,
  `frame` varchar(32) NOT NULL DEFAULT '0',
  `time` datetime NOT NULL,
  `number` varchar(32) NOT NULL,
  `type` tinyint(1) NOT NULL,
  `total` decimal(16, 4) NOT NULL,
  `cost` decimal(16, 4) NOT NULL DEFAULT 0.0000,
  `people` varchar(32) NULL DEFAULT NULL,
  `logistics` text NULL,
  `file` text NULL,
  `data` varchar(265) NULL DEFAULT NULL,
  `more` text NULL,
  `examine` tinyint(1) NOT NULL,
  `cse` tinyint(1) NOT NULL,
  `check` tinyint(1) NOT NULL,
  `user` varchar(32) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `entry_info` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NOT NULL,
  `goods` varchar(32) NOT NULL,
  `attr` varchar(64) NULL DEFAULT NULL,
  `unit` varchar(32) NOT NULL,
  `warehouse` varchar(32) NULL DEFAULT NULL,
  `batch` varchar(32) NULL DEFAULT NULL,
  `mfd` date NULL DEFAULT NULL,
  `price` decimal(12, 4) NOT NULL,
  `nums` decimal(12, 4) NOT NULL,
  `serial` text NULL,
  `total` decimal(12, 4) NOT NULL,
  `data` varchar(256) NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `extry` (
  `id` varchar(32) NOT NULL,
  `customer` varchar(32) NOT NULL,
  `frame` varchar(32) NOT NULL DEFAULT '0',
  `time` datetime NOT NULL,
  `number` varchar(32) NOT NULL,
  `type` tinyint(1) NOT NULL,
  `total` decimal(16, 4) NOT NULL,
  `cost` decimal(16, 4) NOT NULL DEFAULT 0.0000,
  `people` varchar(32) NULL DEFAULT NULL,
  `logistics` text NULL,
  `file` text NULL,
  `data` varchar(265) NULL DEFAULT NULL,
  `more` text NULL,
  `examine` tinyint(1) NOT NULL,
  `cse` tinyint(1) NOT NULL,
  `check` tinyint(1) NOT NULL,
  `user` varchar(32) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `extry_info` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NOT NULL,
  `goods` varchar(32) NOT NULL,
  `attr` varchar(64) NULL DEFAULT NULL,
  `unit` varchar(32) NOT NULL,
  `warehouse` varchar(32) NULL DEFAULT NULL,
  `batch` varchar(32) NULL DEFAULT NULL,
  `mfd` date NULL DEFAULT NULL,
  `price` decimal(12, 4) NOT NULL,
  `nums` decimal(12, 4) NOT NULL,
  `serial` text NULL,
  `total` decimal(12, 4) NOT NULL,
  `data` varchar(256) NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `swap` (
  `id` varchar(32) NOT NULL,
  `frame` varchar(32) NOT NULL DEFAULT '0',
  `time` datetime NOT NULL,
  `number` varchar(32) NOT NULL,
  `total` decimal(16, 4) NOT NULL,
  `cost` decimal(16, 4) NOT NULL DEFAULT 0.0000,
  `logistics` text NULL,
  `people` varchar(32) NULL DEFAULT NULL,
  `file` text NULL,
  `data` varchar(265) NULL DEFAULT NULL,
  `more` text NULL,
  `examine` tinyint(1) NULL DEFAULT 0,
  `cse` tinyint(1) NULL DEFAULT NULL,
  `user` varchar(32) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `swap_info` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NOT NULL,
  `goods` varchar(32) NOT NULL,
  `attr` varchar(64) NULL DEFAULT NULL,
  `unit` varchar(32) NOT NULL,
  `warehouse` varchar(32) NOT NULL,
  `storehouse` varchar(32) NOT NULL,
  `batch` varchar(32) NULL DEFAULT NULL,
  `mfd` date NULL DEFAULT NULL,
  `price` decimal(12, 4) NOT NULL,
  `nums` decimal(12, 4) NOT NULL,
  `serial` text NULL,
  `total` decimal(12, 4) NOT NULL,
  `data` varchar(256) NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `room` (
  `id` varchar(32) NOT NULL,
  `warehouse` varchar(32) NOT NULL,
  `goods` varchar(32) NOT NULL,
  `attr` varchar(64) NULL DEFAULT NULL,
  `nums` decimal(12, 4) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `room_info` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NOT NULL,
  `type` varchar(32) NOT NULL,
  `class` varchar(32) NOT NULL,
  `info` varchar(32) NOT NULL,
  `time` datetime NOT NULL,
  `direction` tinyint(1) NOT NULL,
  `price` decimal(12, 4) NOT NULL,
  `nums` decimal(12, 4) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `batch` (
  `id` varchar(32) NOT NULL,
  `room` varchar(32) NOT NULL,
  `warehouse` varchar(32) NOT NULL,
  `goods` varchar(32) NOT NULL,
  `number` varchar(64) NOT NULL,
  `time` date NOT NULL,
  `nums` decimal(12, 4) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `batch_info` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NOT NULL,
  `type` varchar(32) NOT NULL,
  `class` varchar(32) NOT NULL,
  `info` varchar(32) NOT NULL,
  `direction` tinyint(1) NOT NULL,
  `nums` decimal(12, 4) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `serve` (
  `id` varchar(32) NOT NULL,
  `goods` varchar(32) NOT NULL,
  `attr` varchar(64) NULL DEFAULT NULL,
  `nums` decimal(12, 4) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `serve_info` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NOT NULL,
  `type` varchar(32) NOT NULL,
  `class` varchar(32) NOT NULL,
  `info` varchar(32) NOT NULL,
  `time` datetime NOT NULL,
  `price` decimal(12, 4) NOT NULL,
  `nums` decimal(12, 4) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `summary` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NOT NULL,
  `type` varchar(32) NOT NULL,
  `class` varchar(32) NOT NULL,
  `info` varchar(32) NOT NULL,
  `time` datetime NOT NULL,
  `goods` varchar(32) NOT NULL,
  `attr` varchar(64) NULL DEFAULT NULL,
  `warehouse` varchar(32) NOT NULL,
  `batch` varchar(64) NULL DEFAULT NULL,
  `mfd` date NULL DEFAULT NULL,
  `serial` text NULL,
  `direction` tinyint(1) NOT NULL,
  `price` decimal(12, 4) NOT NULL,
  `nums` decimal(12, 4) NOT NULL,
  `uct` decimal(12, 4) NOT NULL,
  `bct` decimal(12, 4) NOT NULL,
  `exist` text NOT NULL,
  `balance` text NOT NULL,
  `handle` decimal(12, 4) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `log` (
  `id` varchar(32) NOT NULL,
  `time` datetime NOT NULL,
  `user` varchar(32) NOT NULL,
  `info` varchar(256) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `record` (
  `id` varchar(32) NOT NULL,
  `type` varchar(32) NOT NULL,
  `source` varchar(32) NOT NULL,
  `time` datetime NOT NULL,
  `user` varchar(32) NOT NULL,
  `info` varchar(64) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `serial` (
  `id` varchar(32) NOT NULL,
  `room` varchar(32) NOT NULL,
  `warehouse` varchar(32) NOT NULL,
  `batch` varchar(32) NULL DEFAULT NULL,
  `goods` varchar(32) NOT NULL,
  `number` varchar(64) NOT NULL,
  `state` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `serial_info` (
  `id` varchar(32) NOT NULL,
  `pid` varchar(32) NOT NULL,
  `type` varchar(32) NOT NULL,
  `class` varchar(32) NOT NULL,
  `info` varchar(32) NOT NULL,
  PRIMARY KEY (`id`)
);
CREATE TABLE psi_stock_posting_order(sequence BIGINT AUTO_INCREMENT PRIMARY KEY,movement_id VARCHAR(32) NOT NULL UNIQUE);

CREATE TABLE psi_warehouse_posting(kind VARCHAR(16) NOT NULL,document_id VARCHAR(32) NOT NULL,fingerprint VARCHAR(64) NOT NULL,ledger_hash VARCHAR(64) NOT NULL,created_at DATETIME NOT NULL,PRIMARY KEY(kind,document_id));
CREATE TABLE period(id VARCHAR(32) PRIMARY KEY,date DATE,time DATETIME,`user` VARCHAR(32));
CREATE TABLE sys(id VARCHAR(32) PRIMARY KEY,name VARCHAR(64),info TEXT);
CREATE TABLE attr(id VARCHAR(32) PRIMARY KEY,pid VARCHAR(32),name VARCHAR(64),buy DECIMAL(12,4));
CREATE TABLE buy_info(id VARCHAR(32) PRIMARY KEY,pid VARCHAR(32),total DECIMAL(12,4));
CREATE TABLE bre_info(id VARCHAR(32) PRIMARY KEY,pid VARCHAR(32),total DECIMAL(12,4));
CREATE TABLE fifo(id VARCHAR(32) PRIMARY KEY,`out` VARCHAR(32),`in` VARCHAR(32),handle DECIMAL(12,4));
