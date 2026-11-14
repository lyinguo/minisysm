param(
  [string]$JdkPath = 'C:\Program Files\Java\jdk1.8.0_311',
  [string]$MavenPath = 'D:\apache-maven-3.6.1\bin\mvn.cmd'
)
$ErrorActionPreference = 'Stop'
$previousJava = $env:JAVA_HOME
$previousPath = $env:PATH
Push-Location (Join-Path $PSScriptRoot '..\zero-one-12psi\psi-java')
try {
  $env:JAVA_HOME = $JdkPath
  $env:PATH = "$JdkPath\bin;$previousPath"
  & $MavenPath -pl psi-j2-storemanagement test '-Dtest=WarehouseReportDocumentServiceTest' '-DskipTests=false' '-Dmaven.test.skip=false' '-Drevision=1.0.0-SNAPSHOT' -s settings.xml
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
  Pop-Location
  $env:JAVA_HOME = $previousJava
  $env:PATH = $previousPath
}
