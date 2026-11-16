$ErrorActionPreference='Stop'
$loginQaStatePath=Join-Path $PSScriptRoot '.state.json'
$loginQaState=Get-Content $loginQaStatePath -Raw | ConvertFrom-Json
if($loginQaState.database -notmatch '^psi_qa_[0-9a-f]{12}$'){throw 'Not an isolated QA database'}
$loginQaRuntime=Join-Path $PSScriptRoot 'runtime/java'
python (Join-Path $PSScriptRoot 'prepare_login.py')
if($LASTEXITCODE -ne 0){throw 'Login QA configuration generation failed'}
$loginQaPrevious=$loginQaState.login_pid
if($loginQaPrevious -and (Get-Process -Id $loginQaPrevious -ErrorAction SilentlyContinue)){throw 'Recorded login is still live; inspect it before restarting'}
$loginQaSource=Join-Path $loginQaRuntime 'login-project/target/psi-login-1.0.0-SNAPSHOT.jar'
$loginQaJar=Join-Path $loginQaRuntime ('login-'+(Get-Date -Format 'yyyyMMddHHmmssfff')+'.jar')
Copy-Item -LiteralPath $loginQaSource -Destination $loginQaJar
$loginQaConfiguration=([Uri]((Resolve-Path (Join-Path $loginQaRuntime 'login-config')).Path+'\')).AbsoluteUri
$loginQaArguments=@('-Dspring.cloud.bootstrap.enabled=false','-Dspring.cloud.nacos.config.enabled=false','-Dspring.cloud.nacos.discovery.enabled=false','-Dspring.cloud.nacos.discovery.register-enabled=false','-Xms64m','-Xmx256m','-jar',"`"$loginQaJar`"","--spring.config.additional-location=$loginQaConfiguration",'--server.port=18003','--spring.application.name=QA-LOGIN')
$loginQaProcess=Start-Process -FilePath 'C:\Program Files\Java\jdk1.8.0_311\bin\java.exe' -ArgumentList $loginQaArguments -WorkingDirectory $loginQaRuntime -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $loginQaRuntime 'login.out.log') -RedirectStandardError (Join-Path $loginQaRuntime 'login.err.log')
$loginQaState | Add-Member -NotePropertyName login_pid -NotePropertyValue $loginQaProcess.Id -Force
$loginQaState | Add-Member -NotePropertyName login_port -NotePropertyValue 18003 -Force
$loginQaState | ConvertTo-Json -Depth 8 | Set-Content $loginQaStatePath -Encoding UTF8
$loginQaDeadline=(Get-Date).AddSeconds(50)
do {
 if($loginQaProcess.HasExited){throw 'QA login exited; inspect the private startup logs'}
 $loginQaLog=Get-Content (Join-Path $loginQaRuntime 'login.out.log') -Raw -ErrorAction SilentlyContinue
 if($loginQaLog -match 'Started .+ in [0-9.]+ seconds'){Write-Output "QA login ready: port18003 PID=$($loginQaProcess.Id)";return}
 Start-Sleep -Milliseconds 250
}while((Get-Date) -lt $loginQaDeadline)
throw "QA login PID=$($loginQaProcess.Id) remains recorded; readiness observation timed out, inspect this exact process before restarting"
