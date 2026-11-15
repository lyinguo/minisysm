$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot '.state.json'
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.database -notmatch '^psi_qa_[0-9a-f]{12}$') { throw 'Invalid QA database' }
if ($state.supportinfo_pid -and (Get-Process -Id $state.supportinfo_pid -ErrorAction SilentlyContinue)) { throw 'QA supportinfo already running' }
$runtime = Join-Path $PSScriptRoot 'runtime/java'
$source = Join-Path $runtime 'supportinfo-project/target/psi-j7-supportinfo-1.0.0-SNAPSHOT.jar'
$jar = Join-Path $runtime ('supportinfo-' + (Get-Date -Format 'yyyyMMddHHmmssfff') + '.jar')
Copy-Item -LiteralPath $source -Destination $jar
$configUri = ([Uri]((Resolve-Path -LiteralPath $runtime).Path + '\')).AbsoluteUri
$storage = (Join-Path $PSScriptRoot 'runtime/attachments').Replace('\','/')
$arguments = @('-Dspring.cloud.bootstrap.enabled=false', '-Dspring.cloud.nacos.config.enabled=false', '-Dspring.cloud.nacos.discovery.enabled=false', '-Dspring.cloud.nacos.discovery.register-enabled=false', '-Xms64m', '-Xmx384m', '-jar', "`"$jar`"", "--spring.config.additional-location=$configUri", '--server.port=18007', '--spring.application.name=QA-SUPPORTINFO', "--attachments.local-root=$storage")
$process = Start-Process -FilePath 'C:\Program Files\Java\jdk1.8.0_311\bin\java.exe' -ArgumentList $arguments -WorkingDirectory $runtime -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput (Join-Path $runtime 'supportinfo.out.log') -RedirectStandardError (Join-Path $runtime 'supportinfo.err.log')
$state | Add-Member -NotePropertyName supportinfo_pid -NotePropertyValue $process.Id -Force
$state | Add-Member -NotePropertyName supportinfo_port -NotePropertyValue 18007 -Force
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding UTF8
Write-Output "QA supportinfo starting: port=18007 PID=$($process.Id)"
