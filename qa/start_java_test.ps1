param([ValidateSet('store','basic')][string]$Service='store')
$ErrorActionPreference='Stop'
$definition=@{store=@{Module='psi-j2-storemanagement';Port=18020};basic=@{Module='psi-j6-basic_Information';Port=18021}}[$Service]
$statePath=Join-Path $PSScriptRoot '.state.json'
$state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.database -notmatch '^psi_qa_[0-9a-f]{12}$') { throw 'Invalid QA database' }
$runtime=Join-Path $PSScriptRoot 'runtime/java'
$configuration=Get-Content -LiteralPath (Join-Path $runtime 'application.yaml') -Raw
if ($configuration -notmatch ('jdbc:mysql://[^/\r\n]+/'+[regex]::Escape($state.database)+'(?:\?|[\s''"])')) { throw 'Private Java configuration must use the QA database' }
$previous=$state."${Service}_pid"
if ($previous -and (Get-Process -Id $previous -ErrorAction SilentlyContinue)) { throw 'QA service already running; confirm identity before restarting' }
$source=Join-Path $runtime ("$Service-project/target/"+$definition.Module+'-1.0.0-SNAPSHOT.jar')
$jar=Join-Path $runtime ($Service+'-'+(Get-Date -Format 'yyyyMMddHHmmssfff')+'.jar')
Copy-Item -LiteralPath $source -Destination $jar
$configurationUri=([Uri]((Resolve-Path -LiteralPath $runtime).Path+'\')).AbsoluteUri
$arguments=@('-Dspring.cloud.bootstrap.enabled=false','-Dspring.cloud.nacos.config.enabled=false','-Dspring.cloud.nacos.discovery.enabled=false','-Dspring.cloud.nacos.discovery.register-enabled=false','-Xms64m','-Xmx384m','-jar',"`"$jar`"","--spring.config.additional-location=$configurationUri",('--server.port='+$definition.Port),('--spring.application.name=QA-'+$Service.ToUpperInvariant()))
$process=Start-Process -FilePath 'C:\Program Files\Java\jdk1.8.0_311\bin\java.exe' -ArgumentList $arguments -WorkingDirectory $runtime -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime "$Service.out.log") -RedirectStandardError (Join-Path $runtime "$Service.err.log")
$state | Add-Member -NotePropertyName "${Service}_pid" -NotePropertyValue $process.Id -Force
$state | Add-Member -NotePropertyName "${Service}_port" -NotePropertyValue $definition.Port -Force
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding UTF8
Write-Output "QA $Service starting: port=$($definition.Port) PID=$($process.Id)"
