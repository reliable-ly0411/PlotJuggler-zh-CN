# SPDX-License-Identifier: MPL-2.0
# Lightweight syntax and native path/argument checks. Does not run an installer.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$paths = @(Get-ChildItem -LiteralPath (Join-Path $repo 'packaging') -Filter *.ps1 -Recurse)
$paths += @(Get-ChildItem -LiteralPath (Join-Path $repo 'scripts/windows') -Filter *.ps1 -Recurse)
foreach ($path in $paths) {
    $tokens = $null; $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($path.FullName, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
}
$tokens = $null; $parseErrors = $null
$installer = Join-Path $repo 'packaging/installer/build_windows_installer.ps1'
$ast = [System.Management.Automation.Language.Parser]::ParseFile($installer, [ref]$tokens, [ref]$parseErrors)
$find = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Find-AppExe' }, $true)
if (-not $find) { throw 'Missing production Find-AppExe' }
Invoke-Expression $find.Extent.Text
$BuildDir = Join-Path $env:RUNNER_TEMP 'pj packaging 中文 [literal]'
New-Item -ItemType Directory -Force -Path (Join-Path $BuildDir 'RelWithDebInfo') | Out-Null
$app = Join-Path $BuildDir 'RelWithDebInfo/plotjuggler4.exe'
[IO.File]::WriteAllBytes($app, [byte[]]@(1,2,3))
if ((Find-AppExe).FullName -ne $app) { throw 'Production app discovery failed for literal Unicode/space/bracket path' }
$probe = Join-Path $BuildDir 'arguments.py'
$out = Join-Path $BuildDir 'arguments.json'
[IO.File]::WriteAllText($probe, 'import json,sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]), encoding="utf-8")', [Text.UTF8Encoding]::new($false))
$python = (Get-Command python).Source
$p = Start-Process $python -ArgumentList @("`"$probe`"", "`"$out`"", '--root', "`"$BuildDir`"") -Wait -PassThru -NoNewWindow
if ($p.ExitCode -ne 0) { throw 'Native argument probe failed' }
$argsRead = Get-Content -LiteralPath $out -Raw -Encoding utf8 | ConvertFrom-Json
if ($argsRead.Count -ne 2 -or $argsRead[0] -ne '--root' -or $argsRead[1] -ne $BuildDir) { throw 'Installer root argument was split or corrupted' }
Write-Host "PowerShell syntax and native literal-path/argument checks passed ($($paths.Count) scripts)."
