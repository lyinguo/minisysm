$ErrorActionPreference='Stop'
$gatewayQaStatePath=Join-Path $PSScriptRoot '.state.json'
$gatewayQaState=Get-Content $gatewayQaStatePath -Raw | ConvertFrom-Json
if($gatewayQaState.database -notmatch '^psi_qa_[0-9a-f]{12}$'){throw 'Not an isolated QA database'}
$gatewayQaRuntime=Join-Path $PSScriptRoot 'runtime/java'
python (Join-Path $PSScriptRoot 'prepare_gateway.py')
if($LASTEXITCODE -ne 0){throw 'Gateway QA configuration generation failed'}
$gatewayQaPrevious=$gatewayQaState.gateway_pid
if($gatewayQaPrevious -and (Get-Process -Id $gatewayQaPrevious -ErrorAction SilentlyContinue)){throw 'Recorded gateway is still live; inspect it before restarting'}
$gatewayQaSource=Join-Path $gatewayQaRuntime 'gateway-project/target/psi-gateway-1.0.0-SNAPSHOT.jar'
$gatewayQaJar=Join-Path $gatewayQaRuntime ('gateway-'+(Get-Date -Format 'yyyyMMddHHmmssfff')+'.jar')
Copy-Item -LiteralPath $gatewayQaSource -Destination $gatewayQaJar
$gatewayQaConfiguration=([Uri]((Resolve-Path (Join-Path $gatewayQaRuntime 'gateway-config')).Path+'\')).AbsoluteUri
$gatewayQaArguments=@('-Dspring.cloud.bootstrap.enabled=false','-Dspring.cloud.nacos.config.enabled=false','-Dspring.cloud.nacos.discovery.enabled=false','-Dspring.cloud.nacos.discovery.register-enabled=false','-Xms64m','-Xmx256m','-jar',"`"$gatewayQaJar`"","--spring.config.additional-location=$gatewayQaConfiguration",'--server.port=18001','--spring.application.name=QA-GATEWAY')
$gatewayQaProcess=Start-Process -FilePath 'C:\Program Files\Java\jdk1.8.0_311\bin\java.exe' -ArgumentList $gatewayQaArguments -WorkingDirectory $gatewayQaRuntime -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $gatewayQaRuntime 'gateway.out.log') -RedirectStandardError (Join-Path $gatewayQaRuntime 'gateway.err.log')
$gatewayQaState | Add-Member -NotePropertyName gateway_pid -NotePropertyValue $gatewayQaProcess.Id -Force
$gatewayQaState | Add-Member -NotePropertyName gateway_port -NotePropertyValue 18001 -Force
$gatewayQaState | ConvertTo-Json -Depth 8 | Set-Content $gatewayQaStatePath -Encoding UTF8
$gatewayQaDeadline=(Get-Date).AddSeconds(50)
do {
 if($gatewayQaProcess.HasExited){throw 'QA gateway exited; inspect the private startup logs'}
 $gatewayQaLog=Get-Content (Join-Path $gatewayQaRuntime 'gateway.out.log') -Raw -ErrorAction SilentlyContinue
 if($gatewayQaLog -match 'Started .+ in [0-9.]+ seconds'){Write-Output "QA gateway ready: port18001 PID=$($gatewayQaProcess.Id)";return}
 Start-Sleep -Milliseconds 250
}while((Get-Date) -lt $gatewayQaDeadline)
throw "QA gateway PID=$($gatewayQaProcess.Id) remains recorded; readiness observation timed out, inspect this exact process before restarting"
