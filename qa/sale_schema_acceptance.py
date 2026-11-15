"""Boot the real candidate against a new, disposable QA schema to verify rate widening."""
import json
import re
import shutil
import subprocess
import uuid
from decimal import Decimal
from pathlib import Path
import yaml
from acceptance import ROOT, QA, Suite, read_state, sql, integrity


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def check_startup():
    state = dict(read_state())
    state['database'] = 'psi_qa_' + uuid.uuid4().hex[:12]
    assert re.fullmatch(r'psi_qa_[0-9a-f]{12}', state['database'])
    directory = QA / 'runtime/java' / ('sale-schema-probe-' + uuid.uuid4().hex[:10])
    directory.mkdir(parents=True)
    configuration = yaml.safe_load((QA / 'runtime/java/application.yaml').read_text(encoding='utf-8-sig'))
    datasource = configuration['spring']['datasource']
    for options in [datasource, datasource['druid']]:
        options['url'], changed = re.subn(r'(jdbc:mysql://[^/]+/)[^?]+', lambda match: match[1] + state['database'], options['url'])
        assert changed == 1
    (directory / 'application.yaml').write_text(yaml.safe_dump(configuration, allow_unicode=True), encoding='utf-8')
    candidate = QA / 'runtime/java/sale-project/target/psi-sale-1.0.0-SNAPSHOT.jar'
    shutil.copy2(str(candidate), str(directory / 'probe.jar'))
    script = directory / 'probe.ps1'
    script.write_text("""$ErrorActionPreference='Stop'
$directory=DIR_VALUE
$jar=Join-Path $directory 'probe.jar'
if(Get-NetTCPConnection -LocalPort 18024 -State Listen -ErrorAction SilentlyContinue){throw 'Probe port is occupied'}
$java='C:/Program Files/Java/jdk1.8.0_311/bin/java.exe'
$uri=([Uri]($directory+[IO.Path]::DirectorySeparatorChar)).AbsoluteUri
$arguments=@('-Dspring.cloud.bootstrap.enabled=false','-Dspring.cloud.nacos.config.enabled=false','-Dspring.cloud.nacos.discovery.enabled=false','-Dspring.cloud.nacos.discovery.register-enabled=false','-Xms64m','-Xmx256m','-jar',('"'+$jar+'"'),('--spring.config.additional-location='+$uri),'--server.port=18024','--spring.application.name=QA-SALE-SCHEMA-PROBE')
$process=Start-Process -FilePath $java -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $directory 'startup.out.log') -RedirectStandardError (Join-Path $directory 'startup.err.log')
try {
 $ready=$false
 for($attempt=0;$attempt -lt 45;$attempt++) {
  if($process.HasExited){throw 'Schema probe exited before startup completed'}
  $listener=Get-NetTCPConnection -LocalPort 18024 -State Listen -ErrorAction SilentlyContinue|Where-Object OwningProcess -eq $process.Id
  if($listener){$ready=$true;break}
  Start-Sleep -Milliseconds 1000
 }
 if(!$ready){throw 'Schema probe startup timed out'}
 Write-Output 'Candidate Spring service completed initialization on dedicated port'
} finally {
 $current=Get-CimInstance Win32_Process -Filter ("ProcessId="+$process.Id)
 if($current) {
  if($current.Name -ne 'java.exe' -or $current.CommandLine.IndexOf($jar,[StringComparison]::OrdinalIgnoreCase) -lt 0){throw 'Refusing to stop an unexpected process'}
  Stop-Process -Id $process.Id -Force
  $null=$process.WaitForExit(10000)
 }
}
""".replace('DIR_VALUE', quote(directory)), encoding='utf-8-sig')
    integrity.query(state['container'], None, 'CREATE DATABASE `' + state['database'] + '` CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci;')
    try:
        schema_path = ROOT / 'database/schema.sql'
        if not schema_path.exists(): schema_path = ROOT / '.publication/database/schema.sql'
        sql(state, schema_path.read_text(encoding='utf-8'))
        sql(state, "INSERT INTO sell_info(id,pid,goods,unit,price,nums,total,tpt,tax,discount) VALUES('probe-a','fixture','fixture','unit',1,1,1,1,0.13,0.95),('probe-b','fixture','fixture','unit',1,1,1,1,13.00,95.00);")
        result = subprocess.run(['powershell.exe', '-NoProfile', '-File', str(script)], capture_output=True, text=True, timeout=65)
        assert result.returncode == 0, 'Candidate did not start against original schema; inspect private probe logs'
        definitions = sql(state, "SELECT CONCAT(COLUMN_NAME,':',NUMERIC_PRECISION,':',NUMERIC_SCALE) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sell_info' AND COLUMN_NAME IN ('tax','discount') ORDER BY COLUMN_NAME;")
        assert definitions.splitlines() == ['discount:7:4', 'tax:7:4'], 'Candidate did not widen original rate fields'
        values = sql(state, "SELECT CONCAT(tax,',',discount) FROM sell_info ORDER BY id;").splitlines()
        assert [list(map(Decimal, row.split(','))) for row in values] == [[Decimal('.13'), Decimal('.95')], [Decimal('13'), Decimal('95')]], 'Precision migration changed existing business values'
        return ['Real Spring candidate starts on 18024 against a fresh, original-format QA schema', 'Both rates widen to four decimals while old fractional and percent values remain numerically unchanged', 'Probe process identity verified before stopping; only its generated disposable QA database removed']
    finally:
        assert re.fullmatch(r'psi_qa_[0-9a-f]{12}', state['database'])
        integrity.query(state['container'], None, 'DROP DATABASE `' + state['database'] + '`;')


if __name__ == '__main__':
    reporter = Suite.__new__(Suite)
    reporter.results = []
    reporter.case('sale.schema_real_startup_preserves_rates', check_startup)
    reporter.write_report()
