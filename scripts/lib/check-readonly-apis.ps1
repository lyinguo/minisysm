param(
  [string]$BaseUrl = 'http://127.0.0.1:10001',
  [string]$Username = $env:PSI_USERNAME,
  [string]$Password = $env:PSI_PASSWORD
)
$ErrorActionPreference = 'Stop'
if (!$Username -or !$Password) { throw 'Set PSI_USERNAME and PSI_PASSWORD locally before running.' }
$results = [System.Collections.Generic.List[object]]::new()
try {
  $login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/login/auth-login" -Body @{
    username = $Username; password = $Password
  } -TimeoutSec 15
  if ($login.code -ne 10000 -or !$login.data.token) { throw 'Login failed; verify credentials and OAUTH2 service.' }
  $headers = @{ Authorization = "Bearer $($login.data.token)" }
} catch { Write-Error 'Login failed. Check gateway and authentication service.'; exit 1 }

# Only extract literal GET checks. Never execute the original CRUD test script.
$source = @'
Test-Get 'dict-type-list' '/j1-sysc/dictionary-manager/dict-queryList-type?pageIndex=1&pageSize=5'
Test-Get 'dict-list' '/j1-sysc/dictionary-manager/dict-queryList?pageIndex=1&pageSize=5'
Test-Get 'menu-tree' '/j1-sysc/menu-manager/query-menuTree'
Test-Get 'menu-list' '/j1-sysc/menu-manager/query-menuList'
Test-Get 'import-template-list' '/j1-sysc/import-template/list?pageIndex=1&pageSize=5'
Test-Get 'frame-tree' '/basic_information/frame/getFrame'
Test-Get 'warehouse-names' '/basic_information/warehouse/getWarehouseNameList'
Test-Get 'warehouse-list' '/basic_information/warehouse/query-list?pageIndex=1&pageSize=5'
Test-Get 'customer-list' '/basic_information/customer/query-all?pageIndex=1&pageSize=5'
Test-Get 'supplier-list' '/basic_information/supplier/querySupplierList?pageIndex=1&pageSize=5'
Test-Get 'goods-list' '/goods/query-list?pageIndex=1&pageSize=5'
Test-Get 'goods-category-tree' '/goods/category-tree'
Test-Get 'account-list' '/account/list?pageIndex=1&pageSize=5'
Test-Get 'payment' '/payment-order/query-all?pageIndex=1&pageSize=3'
Test-Get 'transfer' '/allot/getAllotList?pageIndex=1&pageSize=3'
Test-Get 'writeoff' '/verification-sheet/list/bill-written?pageIndex=1&pageSize=3'
Test-Get 'cash-bank' '/j5-reportmanagement/cash-bank-statement?pageIndex=1&pageSize=3'
Test-Get 'receivable' '/j5-reportmanagement/detailed-account-receivable-statement?pageIndex=1&pageSize=3'
Test-Get 'payable' '/j5-reportmanagement/detailed-account-payable-statement/query?pageIndex=1&pageSize=3'
Test-Get 'other-ie' '/j5-reportmanagement/other-income-expenditure/query?pageIndex=1&pageSize=3'
Test-Get 'customer-stmt' '/j5-reportmanagement/customer-statement?pageIndex=1&pageSize=3'
Test-Get 'supplier-stmt' '/j5-reportmanagement/supplier-statement?pageIndex=1&pageSize=3'
Test-Get 'profit' '/j5-reportmanagement/profit?pageIndex=1&pageSize=3'
Test-Get 'debt' '/j5-reportmanagement/unit-arrears-report-form?pageIndex=1&pageSize=3'
Test-Get 'wh-balance' '/report/balance/select?pageIndex=1&pageSize=3'
Test-Get 'wh-detail' '/report/detail/list?pageIndex=1&pageSize=3&startTime=2025-01-01&endTime=2026-12-31'
Test-Get 'wh-summary' '/report/summary/list?pageIndex=1&pageSize=3'
Test-Get 'purchase-track' '/j5-reportmanagement/purchase-order-tracking-form?pageIndex=1&pageSize=3&type=0'
Test-Get 'sale-track' '/j5-reportmanagement/sales-order-tracking-form?pageIndex=1&pageSize=3&type=0'
Test-Get 'purchase' '/j3-purchase/purchase-note/list?pageIndex=1&pageSize=3'
Test-Get 'other-income' '/finance/other-income/list?pageIndex=1&pageSize=3'
Test-Get 'other-expense' '/finance/other-expense/list?pageIndex=1&pageSize=3'
Test-Get 'trade-expense' '/finance/trade-expense/list?pageIndex=1&pageSize=3'
Test-Get 'trade-invoice' '/finance/trade-invoice/list/report?pageIndex=1&pageSize=3'
'@
$source += @'

Test-Get 'purchase-payment' '/j5-reportmanagement/procurement-payment-form?pageIndex=1&pageSize=3'
Test-Get 'purchase-summary' '/j5-reportmanagement/purchase-order-summary-form?pageIndex=1&pageSize=3'
Test-Get 'purchase-detail' '/j5-reportmanagement/procurement-detail-form/query?pageIndex=1&pageSize=3'
Test-Get 'purchase-ranking' '/j5-reportmanagement/purchase-ranking-form?pageIndex=1&pageSize=3'
Test-Get 'sale-receipt' '/j5-reportmanagement/sales-receipt?pageIndex=1&pageSize=3'
Test-Get 'sale-summary' '/j5-reportmanagement/sales-summary?pageIndex=1&pageSize=3'
Test-Get 'sale-detail' '/j5-reportmanagement/sales-detail-form/query?pageIndex=1&pageSize=3'
Test-Get 'sale-ranking' '/j5-reportmanagement/sales-ranking-table?pageIndex=1&pageSize=3'
Test-Get 'warehouse-inbound-documents' '/transfer/report-documents/entry?pageIndex=1&pageSize=3'
Test-Get 'warehouse-outbound-documents' '/transfer/report-documents/extry?pageIndex=1&pageSize=3'
Test-Get 'warehouse-transfer-documents' '/transfer/report-documents/swap?pageIndex=1&pageSize=3'
'@
$checks = [regex]::Matches($source, "(?m)^Test-Get '([^']+)' '([^']+)'")
foreach ($check in $checks) {
  $name = $check.Groups[1].Value
  $path = $check.Groups[2].Value
  try {
    $response = Invoke-WebRequest -Uri "$BaseUrl$path" -Headers $headers -UseBasicParsing -TimeoutSec 8
    $body = $response.Content | ConvertFrom-Json
    $passed = $body.code -eq 10000
    $results.Add([pscustomobject]@{ Name = $name; Path = $path; Passed = $passed; Code = $body.code })
    Write-Host "$name code=$($body.code)"
  } catch {
    $results.Add([pscustomobject]@{ Name = $name; Path = $path; Passed = $false; Code = 'HTTP_OR_NETWORK_ERROR' })
    Write-Host "$name HTTP_OR_NETWORK_ERROR"
  }
}
New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot '..\logs') | Out-Null
$output = Join-Path $PSScriptRoot '..\logs\readonly-api-results.json'
$results | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $output -Encoding UTF8
$passedCount = @($results | Where-Object Passed).Count
Write-Host "RESULT passed=$passedCount total=$($results.Count) report=$output"
if ($passedCount -ne $results.Count) { exit 1 }
