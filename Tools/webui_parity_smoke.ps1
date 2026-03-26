param(
    [string]$WebUiBase = "http://127.0.0.1:8765",
    [string]$AuthUser = "",
    [string]$AuthToken = "",
    [string]$TemplateName = "",
    [int]$BotId = -1
)

$ErrorActionPreference = "Stop"

function Invoke-JsonGet {
    param([string]$Url)
    (Invoke-WebRequest -UseBasicParsing -Uri $Url -Method GET -TimeoutSec 20).Content | ConvertFrom-Json
}

function Invoke-UiPost {
    param([string]$Path, [hashtable]$Body)
    $json = $Body | ConvertTo-Json -Depth 10
    $resp = Invoke-WebRequest -UseBasicParsing -Uri ($WebUiBase.TrimEnd('/') + $Path) -Method POST -ContentType "application/json" -Body $json -TimeoutSec 30
    if (-not $resp.Content) { return $null }
    return ($resp.Content | ConvertFrom-Json)
}

function Invoke-Ts3Call {
    param([object[]]$Segments)
    $body = @{ segments = $Segments }
    if ($AuthUser) { $body.authUser = $AuthUser }
    if ($AuthToken) { $body.authToken = $AuthToken }
    Invoke-UiPost -Path "/api/ts3ab/call" -Body $body
}

function Invoke-BotCall {
    param([int]$Id, [object[]]$Command)
    $body = @{ botId = $Id; command = $Command }
    if ($AuthUser) { $body.authUser = $AuthUser }
    if ($AuthToken) { $body.authToken = $AuthToken }
    Invoke-UiPost -Path "/api/ts3ab/bot_call" -Body $body
}

function Step {
    param([string]$Name, [scriptblock]$Action)
    try {
        $result = & $Action
        Write-Host ("[PASS] " + $Name) -ForegroundColor Green
        return [pscustomobject]@{ Name = $Name; Ok = $true; Error = ""; Result = $result }
    } catch {
        Write-Host ("[FAIL] " + $Name + " -> " + $_.Exception.Message) -ForegroundColor Red
        return [pscustomobject]@{ Name = $Name; Ok = $false; Error = $_.Exception.Message; Result = $null }
    }
}

$results = @()

$results += Step "UI Root" { Invoke-JsonGet -Url ($WebUiBase.TrimEnd('/') + "/api/ts3ab/status") | Out-Null; $true }
$results += Step "Versions CSV" { Invoke-JsonGet -Url ($WebUiBase.TrimEnd('/') + "/api/ts3ab/versions?force=1") | Out-Null; $true }
$results += Step "Recordings dirs" { Invoke-JsonGet -Url ($WebUiBase.TrimEnd('/') + "/api/recordings/dirs") | Out-Null; $true }
$results += Step "Recordings sessions" { Invoke-JsonGet -Url ($WebUiBase.TrimEnd('/') + "/api/sessions") | Out-Null; $true }

$results += Step "TS3 version" { Invoke-Ts3Call -Segments @("version") | Out-Null; $true }
$results += Step "TS3 system info" { Invoke-Ts3Call -Segments @("system", "info") | Out-Null; $true }
$results += Step "TS3 bot list" { Invoke-Ts3Call -Segments @("bot", "list") | Out-Null; $true }
$results += Step "TS3 auth probe json merge" { Invoke-Ts3Call -Segments @("json", "merge") | Out-Null; $true }

if ($TemplateName) {
    $results += Step "TS3 offline settings get" { Invoke-Ts3Call -Segments @("settings", "bot", "get", $TemplateName) | Out-Null; $true }
}

if ($BotId -ge 0) {
    $results += Step "Bot info" { Invoke-BotCall -Id $BotId -Command @("bot", "info") | Out-Null; $true }
    $results += Step "Bot song" { Invoke-BotCall -Id $BotId -Command @("song") | Out-Null; $true }
    $results += Step "Bot server tree" { Invoke-BotCall -Id $BotId -Command @("server", "tree") | Out-Null; $true }
    $results += Step "Bot settings get" { Invoke-BotCall -Id $BotId -Command @("settings", "get") | Out-Null; $true }
    $results += Step "Bot list list" { Invoke-BotCall -Id $BotId -Command @("list", "list") | Out-Null; $true }
}

$ok = @($results | Where-Object { $_.Ok }).Count
$all = $results.Count
Write-Host ""
Write-Host ("Smoke summary: {0}/{1} passed" -f $ok, $all) -ForegroundColor Cyan

if ($ok -ne $all) {
    exit 1
}
