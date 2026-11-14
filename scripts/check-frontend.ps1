param([switch]$Build)
$ErrorActionPreference = 'Stop'
$frontend = Join-Path $PSScriptRoot '..\zero-one-12psi\psi-frontend'
Push-Location $frontend
try {
  & pnpm.cmd exec vue-tsc --build --pretty false
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & pnpm.cmd exec vitest run src/views/report/report-routes.test.ts src/views/report/purchase/PurchaseSummary.navigation.test.ts src/plugins/http.auth.test.ts src/utils/printDocument.test.ts src/components/RoutePageBoundary.test.ts src/apis/api-regressions.test.ts src/components/warehouse/WarehouseDocumentReport.test.ts src/views/advancedSettings/summary/DataVerification.test.ts
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  if ($Build) {
    & pnpm.cmd exec vite build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
} finally { Pop-Location }
