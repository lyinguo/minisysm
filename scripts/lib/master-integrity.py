"""Install/test cross-service master-data integrity without rewriting business records."""
import argparse
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / 'database/migrations/20261114_master_integrity.sql'
# Only relational IDs, never supplier.account/customer.account (bank account text).
REFS = {
    'annex': [('user', 'img')],
    'customer': [('bill', 'customer'), ('extry', 'customer'), ('ice', 'customer'),
                 ('imy', 'customer'), ('sell', 'customer'), ('sor', 'customer'), ('sre', 'customer')],
    'supplier': [('bill', 'supplier'), ('bor', 'supplier'), ('bre', 'supplier'),
                 ('buy', 'supplier'), ('entry', 'supplier'), ('oce', 'supplier'), ('omy', 'supplier')],
    'goods': [(t, 'goods') for t in ['batch', 'bor_info', 'bre_info', 'buy_info', 'entry_info',
              'extry_info', 'room', 'sell_info', 'serial', 'serve', 'sor_info', 'sre_info', 'summary', 'swap_info']] + [('attr', 'pid')],
    'warehouse': [(t, 'warehouse') for t in ['batch', 'bor_info', 'bre_info', 'buy_info', 'entry_info',
                  'extry_info', 'room', 'sell_info', 'serial', 'sor_info', 'sre_info', 'summary', 'swap_info']]
                  + [('swap_info', 'storehouse')],
    'account': [(t, 'account') for t in ['allot_info', 'bre', 'buy', 'ice', 'imy_info', 'oce',
                'omy_info', 'sell', 'sre']] + [('account_info', 'pid')],
    'dict_type': [('dict', 'tid')],
    'menu': [('menu', 'pid'), ('func_perm', 'mid')],
    'role': [('user', 'role')],
    'people': [(t, 'people') for t in ['allot', 'bill', 'bor', 'bre', 'buy', 'entry', 'extry', 'ice',
                'imy', 'oce', 'omy', 'sell', 'sor', 'sre', 'swap']],
    'frame': [(t, 'frame') for t in ['account', 'allot', 'bill', 'bor', 'bre', 'buy', 'customer', 'entry',
               'extry', 'ice', 'imy', 'oce', 'omy', 'people', 'sell', 'sor', 'sre', 'supplier', 'swap', 'user', 'warehouse']]
               + [('frame', 'pid')],
    'user': [(t, 'user') for t in ['allot', 'bill', 'bor', 'bre', 'buy', 'customer', 'entry', 'extry', 'ice',
              'imy', 'log', 'oce', 'often', 'omy', 'period', 'record', 'sell', 'sor', 'sre', 'supplier', 'swap']]
}


def build_sql():
    out = ['-- Cross-service integrity guards. No business rows are deleted or rewritten.',
           '-- Empty/0 optional legacy references are tolerated. New nonempty IDs must exist.',
           '-- Install during maintenance; DDL is not transactional. Use master-integrity.py.',
           'DELIMITER $$',
           'DROP PROCEDURE IF EXISTS psi_install_parent_refs$$',
           '''CREATE PROCEDURE psi_install_parent_refs() BEGIN
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
END$$''', 'SET @psi_previous_fk_checks=@@FOREIGN_KEY_CHECKS$$',
           'SET SESSION FOREIGN_KEY_CHECKS=0$$', 'CALL psi_install_parent_refs()$$',
           'SET SESSION FOREIGN_KEY_CHECKS=@psi_previous_fk_checks$$', 'DROP PROCEDURE psi_install_parent_refs$$']
    for parent, refs in REFS.items():
        name = 'psi_guard_del_' + parent
        body = ['DECLARE hit_id VARCHAR(32) DEFAULT NULL;', 'DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id = NULL;']
        if parent == 'user':
            body += ["IF OLD.`user`='admin' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:reserved:user'; END IF;"]
        if parent == 'menu':
            body += ["SELECT id INTO hit_id FROM role WHERE JSON_CONTAINS_PATH(IF(JSON_VALID(root),root,'{}'),'one',CONCAT('$.',JSON_QUOTE(OLD.id))) LIMIT 1 FOR UPDATE;",
                     "IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:menu:role'; END IF;"]
        if parent in ('customer', 'supplier', 'account'):
            body += ["IF COALESCE(OLD.balance,0) <> 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:balance:" + parent + "'; END IF;"]
        for table, column in refs:
            # MySQL forbids locking a table already modified by the invoking statement.
            lock = '' if table == parent else ' FOR UPDATE'
            condition = f'`{column}`=OLD.id'
            if parent == 'user':
                condition += f" OR (OLD.`user` NOT IN ('','0') AND `{column}`=OLD.`user`)"
            body += ['SET hit_id = NULL;',
                     f'SELECT id INTO hit_id FROM `{table}` WHERE {condition} LIMIT 1{lock};',
                     f"IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:referenced:{parent}:{table}'; END IF;"]
        out += [f'DROP TRIGGER IF EXISTS `{name}`$$',
                f'CREATE TRIGGER `{name}` BEFORE DELETE ON `{parent}` FOR EACH ROW BEGIN\n' + '\n'.join(body) + '\nEND$$']
        name = 'psi_guard_id_' + parent
        login_guard = "IF NOT (NEW.`user` <=> OLD.`user`) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:login:user'; END IF;" if parent == 'user' else ''
        out += [f'DROP TRIGGER IF EXISTS `{name}`$$',
                f"CREATE TRIGGER `{name}` BEFORE UPDATE ON `{parent}` FOR EACH ROW BEGIN IF NOT (NEW.id <=> OLD.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:immutable:{parent}'; END IF; {login_guard} END$$"]
    children = {}
    for parent, refs in REFS.items():
        for table, column in refs:
            children.setdefault(table, []).append((column, parent))
    for table, refs in children.items():
        for event in ['INSERT', 'UPDATE']:
            name = f'psi_guard_{event.lower()}_{table}'
            body = ['DECLARE parent_id VARCHAR(32) DEFAULT NULL;', 'DECLARE ancestor_id VARCHAR(32) DEFAULT NULL;',
                    'DECLARE depth INT DEFAULT 0;', 'DECLARE CONTINUE HANDLER FOR NOT FOUND SET parent_id = NULL;']
            for column, parent in refs:
                changed = f'NOT (NEW.`{column}` <=> OLD.`{column}`) AND ' if event == 'UPDATE' else ''
                lock = '' if parent == table else ' LOCK IN SHARE MODE'
                if parent == table:
                    body += [f'SET ancestor_id=NEW.`{column}`; SET depth=0;',
                             "WHILE ancestor_id IS NOT NULL AND ancestor_id NOT IN ('','0') AND depth < 1000 DO",
                             f"IF ancestor_id=NEW.id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:{parent}'; END IF;",
                             f'SET parent_id=NULL; SELECT `{column}` INTO parent_id FROM `{parent}` WHERE id=ancestor_id;',
                             'SET ancestor_id=parent_id; SET depth=depth+1; END WHILE;',
                             f"IF depth >= 1000 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:cycle:{parent}'; END IF;"]
                condition = f'id=NEW.`{column}`'
                if parent == 'user':
                    condition += f' OR `user`=NEW.`{column}`'
                body += [f"IF {changed}NEW.`{column}` IS NOT NULL AND NEW.`{column}` NOT IN ('','0') THEN",
                         'SET parent_id = NULL;',
                         f'SELECT id INTO parent_id FROM `{parent}` WHERE {condition} LIMIT 1{lock};',
                         f"IF parent_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'PSI_INTEGRITY:missing:{parent}'; END IF; END IF;"]
            out += [f'DROP TRIGGER IF EXISTS `{name}`$$',
                    f'CREATE TRIGGER `{name}` BEFORE {event} ON `{table}` FOR EACH ROW BEGIN\n' + '\n'.join(body) + '\nEND$$']
    for event in ['UPDATE', 'DELETE']:
        name = 'psi_guard_fun_' + event.lower()
        condition = "OLD.name='fun'" + (" AND (NOT (NEW.info <=> OLD.info) OR NOT (NEW.name <=> OLD.name))" if event == 'UPDATE' else '')
        out += [f'DROP TRIGGER IF EXISTS `{name}`$$',
                f"CREATE TRIGGER `{name}` BEFORE {event} ON sys FOR EACH ROW BEGIN IF {condition} THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:readonly:sys'; END IF; END$$"]
    body = ['DECLARE hit_id VARCHAR(32) DEFAULT NULL;', 'DECLARE CONTINUE HANDLER FOR NOT FOUND SET hit_id=NULL;',
            'IF NOT (NEW.initial <=> OLD.initial) THEN']
    for table, column in REFS['account']:
        body += ['SET hit_id=NULL;', f'SELECT id INTO hit_id FROM `{table}` WHERE `{column}`=OLD.id LIMIT 1 FOR UPDATE;',
                 "IF hit_id IS NOT NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='PSI_INTEGRITY:initial:account'; END IF;"]
    body.append('END IF;')
    out += ['DROP TRIGGER IF EXISTS psi_guard_initial_account$$',
            'CREATE TRIGGER psi_guard_initial_account BEFORE UPDATE ON account FOR EACH ROW BEGIN\n'+'\n'.join(body)+'\nEND$$']
    return '\n\n'.join(out) + '\nDELIMITER ;\n'


def command(container, database=None):
    # Credentials remain inside the existing container, never in arguments/output.
    cmd = ['docker', 'exec', '-i', container, 'sh', '-c',
           'export MYSQL_PWD="${MYSQL_ROOT_PASSWORD}"; exec mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names "$@"', 'sh']
    if database:
        cmd.append(database)
    return cmd


def query(container, database, sql, check=True):
    result = subprocess.run(command(container, database), input=sql, text=True, encoding='utf-8', capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result


def install(container, database):
    sql = MIGRATION.read_text(encoding='utf-8')
    digest = hashlib.sha256(sql.encode()).hexdigest()
    # Preflight before any DROP TRIGGER. A missing table/column must stop installation.
    preflight = ['SELECT id,name,info FROM sys LIMIT 0;', 'SELECT initial FROM account LIMIT 0;']
    for parent, refs in REFS.items():
        fields = 'id,balance' if parent in ('customer', 'supplier', 'account') else 'id'
        preflight.append(f'SELECT {fields} FROM `{parent}` LIMIT 0;')
        for table, column in refs:
            preflight.append(f'SELECT id,`{column}` FROM `{table}` LIMIT 0;')
    query(container, database, '\n'.join(preflight))
    for table in ['frame', 'menu']:
        count = query(container, database, f"SELECT COUNT(*) FROM `{table}` c LEFT JOIN `{table}` p ON p.id=c.pid WHERE c.pid IS NOT NULL AND c.pid NOT IN ('','0') AND p.id IS NULL;").stdout.strip()
        if count != '0':
            print(f'WARNING {table}: {count} historical orphan parents preserved; new invalid references will be blocked.')
    query(container, database, 'CREATE TABLE IF NOT EXISTS psi_schema_migration (id VARCHAR(80) PRIMARY KEY, digest VARCHAR(64) NOT NULL, installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
    previous = query(container, database, "SELECT digest FROM psi_schema_migration WHERE id='20261114_master_integrity';").stdout.strip()
    expected = sql.count('CREATE TRIGGER')
    actual = int(query(container, database, "SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema=DATABASE() AND trigger_name LIKE 'psi_guard_%';").stdout.strip())
    if previous == digest and actual == expected:
        print(f'Integrity guards already installed ({actual} triggers).')
        return
    query(container, database, sql)
    query(container, database, "REPLACE INTO psi_schema_migration(id,digest) VALUES('20261114_master_integrity','" + digest + "');")
    print(f'Installed {expected} integrity triggers; existing business rows preserved.')


def audit(container, database):
    statements = []
    for table in ['customer', 'supplier', 'goods', 'warehouse', 'account']:
        statements.append(f"SELECT 'duplicate_numbers:{table}',COUNT(*) FROM (SELECT number FROM `{table}` GROUP BY number HAVING COUNT(*)>1) duplicates;")
    for parent, refs in REFS.items():
        for table, column in refs:
            join = f'p.id=c.`{column}`'
            if parent == 'user':
                join += f' OR p.`user`=c.`{column}`'
            statements.append(f"SELECT '{table}.{column}->{parent}',COUNT(*) FROM `{table}` c LEFT JOIN `{parent}` p ON ({join}) WHERE c.`{column}` IS NOT NULL AND c.`{column}` NOT IN ('','0') AND p.id IS NULL;")
    result = query(container, database, '\n'.join(statements))
    counts = {}
    for line in result.stdout.splitlines():
        name, count = line.rsplit('\t', 1)
        counts[name] = int(count)
    print(json.dumps({'checks': len(counts), 'nonzero_findings': {key: value for key, value in counts.items() if value}, 'business_records_printed': False}, ensure_ascii=False, indent=2))


def test(container):
    database = 'psi_integrity_test_' + uuid.uuid4().hex[:12]
    query(container, None, f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4;')
    passed = 0
    try:
        tables = {parent: {'id', 'balance'} for parent in REFS}
        tables['role'].add('root')
        tables['user'].add('user')
        tables['sys'] = {'id', 'name', 'info'}
        tables['account'].add('initial')
        for refs in REFS.values():
            for table, column in refs:
                tables.setdefault(table, {'id'}).add(column)
        schema = '\n'.join('CREATE TABLE `' + table + '` (' + ','.join(
            '`' + c + '` ' + ('DECIMAL(16,4) DEFAULT 0' if c in ('balance','initial') else "VARCHAR(32) DEFAULT ''") + (' PRIMARY KEY' if c == 'id' else '')
            for c in sorted(cols)) + ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;' for table, cols in tables.items())
        query(container, database, schema)
        query(container, database, MIGRATION.read_text(encoding='utf-8'))
        query(container, database, '''DELIMITER $$
CREATE PROCEDURE psi_test_blocked(IN test_sql TEXT, IN expected VARCHAR(255)) BEGIN
DECLARE failed BOOL DEFAULT FALSE;
DECLARE reason TEXT DEFAULT '';
BEGIN
DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN
GET DIAGNOSTICS CONDITION 1 reason=MESSAGE_TEXT;
SET failed=TRUE;
END;
SET @psi_test_statement=test_sql;
PREPARE stmt FROM @psi_test_statement;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
END;
IF NOT failed OR reason NOT LIKE CONCAT('%',expected,'%') THEN
SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Integrity test: expected rejection was not observed';
END IF;
END$$
DELIMITER ;''')
        statements = []
        def flush():
            if statements:
                query(container, database, '\n'.join(statements))
                statements.clear()
        def ok(sql):
            nonlocal passed
            statements.append(sql)
            passed += 1
        def blocked(sql, reason):
            nonlocal passed
            literal = 'CONVERT(0x' + sql.encode('utf-8').hex() + ' USING utf8mb4)'
            statements.append(f"CALL psi_test_blocked({literal},'{reason}');")
            passed += 1
        for parent in REFS:
            if parent == 'user':
                ok("INSERT INTO `user`(id,`user`) VALUES('used','author-login'),('unused','unused-login');")
            else:
                ok(f"INSERT INTO `{parent}`(id) VALUES('used'),('unused');")
            ok(f"DELETE FROM `{parent}` WHERE id='unused';")
            blocked(f"UPDATE `{parent}` SET id='changed' WHERE id='used';", 'immutable:' + parent)
        for parent, refs in REFS.items():
            for i, (table, column) in enumerate(refs):
                row = parent + str(i)
                blocked(f"INSERT INTO `{table}`(id,`{column}`) VALUES('{row}','missing');", 'missing:' + parent)
                ok(f"INSERT INTO `{table}`(id,`{column}`) VALUES('{row}','used');")
                blocked(f"DELETE FROM `{parent}` WHERE id='used';", 'referenced:' + parent)
                blocked(f"UPDATE `{table}` SET `{column}`='missing' WHERE id='{row}';", 'missing:' + parent)
                ok(f"DELETE FROM `{table}` WHERE id='{row}';")
            flush()
            print(f'PASS reference rules: {parent}', flush=True)
        for parent in ['customer', 'supplier', 'account']:
            for balance in [-1, 1]:
                ok(f"UPDATE `{parent}` SET balance={balance} WHERE id='used';")
                blocked(f"DELETE FROM `{parent}` WHERE id='used';", 'balance:' + parent)
            ok(f"UPDATE `{parent}` SET balance=0 WHERE id='used';")
        for parent in ['frame', 'menu']:
            blocked(f"UPDATE `{parent}` SET pid='used' WHERE id='used';", 'cycle:' + parent)
            ok(f"INSERT INTO `{parent}`(id,pid) VALUES('child','used');")
            blocked(f"UPDATE `{parent}` SET pid='child' WHERE id='used';", 'cycle:' + parent)
            ok(f"DELETE FROM `{parent}` WHERE id='child';")
        ok("INSERT INTO `user`(id,`user`) VALUES('admin-test','admin');")
        blocked("DELETE FROM `user` WHERE id='admin-test';", 'reserved:user')
        ok("INSERT INTO log(id,`user`) VALUES('legacy-author','author-login');")
        blocked("DELETE FROM `user` WHERE id='used';", 'referenced:user')
        blocked("UPDATE `user` SET `user`='renamed' WHERE id='used';", 'login:user')
        ok("INSERT INTO sys(id,name,info) VALUES('fun','fun','{}');")
        blocked("UPDATE sys SET info='changed' WHERE id='fun';", 'readonly:sys')
        blocked("DELETE FROM sys WHERE id='fun';", 'readonly:sys')
        ok("UPDATE sys SET info='{}' WHERE id='fun';")
        ok("INSERT INTO account_info(id,pid) VALUES('ledger','used');")
        blocked("UPDATE account SET initial=10 WHERE id='used';", 'initial:account')
        # One SQL batch cannot partially delete unused + referenced masters.
        ok("INSERT INTO customer(id) VALUES('batch-free'); INSERT INTO sell(id,customer) VALUES('sale','used');")
        blocked("DELETE FROM customer WHERE id IN ('used','batch-free');", 'referenced:customer')
        flush()
        assert query(container, database, "SELECT COUNT(*) FROM customer WHERE id IN ('used','batch-free');").stdout.strip() == '2'
        passed += 1
        # Concurrent child insertion holds a shared parent lock until commit.
        process = subprocess.Popen(command(container, database), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        process.stdin.write("START TRANSACTION; INSERT INTO buy(id,supplier) VALUES('concurrent','used'); SELECT SLEEP(2); COMMIT;\n")
        process.stdin.close()
        time.sleep(0.5)
        blocked("DELETE FROM supplier WHERE id='used';", 'referenced:supplier')
        flush()
        assert process.wait(timeout=15) == 0, process.stderr.read()
        # Conversely, an insert cannot resurrect a parent deleted concurrently.
        process = subprocess.Popen(command(container, database), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        process.stdin.write("START TRANSACTION; DELETE FROM goods WHERE id='used'; SELECT SLEEP(2); COMMIT;\n")
        process.stdin.close()
        time.sleep(0.5)
        blocked("INSERT INTO room(id,goods) VALUES('late','used');", 'missing:goods')
        flush()
        assert process.wait(timeout=15) == 0, process.stderr.read()
        print(json.dumps({'passed': passed, 'database': 'isolated temporary MySQL database', 'production_writes': False}))
    finally:
        query(container, None, f'DROP DATABASE `{database}`;')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['generate', 'install', 'test', 'audit'])
    parser.add_argument('--container', default='mysql8')
    parser.add_argument('--database', default='zo_psi')
    args = parser.parse_args()
    if args.action == 'generate':
        MIGRATION.parent.mkdir(parents=True, exist_ok=True)
        MIGRATION.write_text(build_sql(), encoding='utf-8')
    elif args.action == 'test':
        test(args.container)
    elif args.action == 'audit':
        audit(args.container, args.database)
    else:
        install(args.container, args.database)
