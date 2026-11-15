$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot '.state.json'
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.database -notmatch '^psi_qa_[0-9a-f]{12}$' -or $state.oauth_port -ne 18002) { throw 'Invalid QA state' }
$java = 'C:\Program Files\Java\jdk1.8.0_311\bin\java.exe'
$runtime = Join-Path $PSScriptRoot 'runtime/java'
$builtJar = Join-Path $runtime 'oauth-project/target/psi-oauth2-1.0.0-SNAPSHOT.jar'
if ($state.oauth_pid -and (Get-Process -Id $state.oauth_pid -ErrorAction SilentlyContinue)) { throw 'QA OAuth is already running; inspect it before restarting' }
$jar = Join-Path $runtime ('oauth-' + (Get-Date -Format 'yyyyMMddHHmmssfff') + '.jar')
Copy-Item -LiteralPath $builtJar -Destination $jar
$configUri = ([Uri]((Resolve-Path -LiteralPath $runtime).Path + '\')).AbsoluteUri
$arguments = @('-Dspring.cloud.bootstrap.enabled=false', '-Dspring.cloud.nacos.config.enabled=false', '-Dspring.cloud.nacos.discovery.enabled=false', '-Dspring.cloud.nacos.discovery.register-enabled=false', '-Xms64m', '-Xmx384m', '-jar', "`"$jar`"", "--spring.config.additional-location=$configUri")
$process = Start-Process -FilePath $java -ArgumentList $arguments -WorkingDirectory $runtime -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput (Join-Path $runtime 'oauth.out.log') -RedirectStandardError (Join-Path $runtime 'oauth.err.log')
$state | Add-Member -NotePropertyName oauth_pid -NotePropertyValue $process.Id -Force
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding UTF8
Write-Output "QA OAuth starting: port=18002 PID=$($process.Id)"
