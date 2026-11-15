param([string]$Module = 'psi-c1-systemparameters', [string]$Service = 'c1')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot
$statePath = Join-Path $PSScriptRoot '.state.json'
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.database -notmatch '^psi_qa_[0-9a-f]{12}$') { throw 'Refusing a non-QA database' }
$port = $state."${Service}_port"
if (!$port -or $port -lt 18000 -or $port -gt 19999) { throw 'Refusing a non-QA port' }
$config = Import-Clixml (Join-Path $PSScriptRoot "runtime/$Service-start.xml")
$databases = [regex]::Matches($config.Arguments, '\bdn=(\S+)')
$ports = [regex]::Matches($config.Arguments, '\bsp=(\d+)')
if ($databases.Count -ne 1 -or $databases[0].Groups[1].Value -ne $state.database -or $ports.Count -ne 1 -or [int]$ports[0].Groups[1].Value -ne $port) {
  throw 'Private test arguments do not match the isolated database and port'
}
$runtimeRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'runtime')) + [IO.Path]::DirectorySeparatorChar
$executable = [IO.Path]::GetFullPath((Get-Content -LiteralPath (Join-Path $PSScriptRoot "runtime/cpp/$Module/latest.txt") -Raw).Trim())
if (!$executable.StartsWith($runtimeRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Executable must stay inside QA runtime' }
$previous = $state."${Service}_pid"
if ($previous) {
  $process = Get-CimInstance Win32_Process -Filter "ProcessId=$previous"
  if ($process) {
    $resolved = [IO.Path]::GetFullPath($process.ExecutablePath)
    if (!$resolved.StartsWith($runtimeRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Refusing to stop a non-QA process' }
    Stop-Process -Id $previous -Force
  }
}
$started = Start-Process -FilePath $executable -ArgumentList $config.Arguments -WorkingDirectory $config.WorkingDirectory -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $PSScriptRoot "runtime/$Service.out.log") `
  -RedirectStandardError (Join-Path $PSScriptRoot "runtime/$Service.err.log") -PassThru
$state | Add-Member -NotePropertyName "${Service}_pid" -NotePropertyValue $started.Id -Force
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding UTF8
Write-Output "QA $Service started: port=$port PID=$($started.Id)"
