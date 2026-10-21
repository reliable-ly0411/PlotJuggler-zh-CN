# SPDX-License-Identifier: MPL-2.0
param([string]$Packages = "pkg", [string]$Output = "reports")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $Output | Out-Null
$outputPath = (Resolve-Path $Output).Path
$installer = @(Get-ChildItem $Packages -Filter *.exe)
if ($installer.Count -ne 1) { throw "Expected exactly one final installer" }
$checksum = Get-Content (Join-Path $Packages "SHA256SUMS-Windows.txt")
$before = (Get-FileHash $installer[0].FullName -Algorithm SHA256).Hash.ToLower()
if (-not $checksum.StartsWith($before)) { throw "Downloaded installer checksum mismatch" }
$root = Join-Path $env:RUNNER_TEMP "pj4-installed-zh"
$p = Start-Process $installer[0].FullName -ArgumentList @("install", "--root", "`"$root`"",
    "--accept-licenses", "--default-answer", "--confirm-command") -Wait -PassThru -NoNewWindow `
    -RedirectStandardOutput (Join-Path $outputPath 'installer.out') `
    -RedirectStandardError (Join-Path $outputPath 'installer.err')
if ($p.ExitCode -ne 0) { throw "Final installer failed: $($p.ExitCode)" }
[xml]$components = Get-Content (Join-Path $root "components.xml")
$installed = ($components.Packages.Package | Where-Object { $_.Name -eq "io.plotjuggler.application" }).Version
$release = Get-Content (Join-Path $root "share/plotjuggler4/release.json") -Raw | ConvertFrom-Json
if ($installed -ne $release.ifw_package_version) { throw "IFW version mismatch" }
$version = (Get-Content versions.env | Where-Object { $_ -match "^PJ_APP_VERSION=" }) -replace "^PJ_APP_VERSION=", ""
python -X utf8 packaging/localization/verify_package.py --prefix $root --executable "$root/bin/PlotJuggler4.exe" `
    --real-bin 3rdparty/plotjuggler-apbin-plugins/tests/logs/00000001.BIN --output "$outputPath/runtime" --expected-source $env:GITHUB_SHA --expected-version $version --capture
if ($LASTEXITCODE -ne 0) { throw "Installed package acceptance failed" }
$p = Start-Process "$root/maintenancetool.exe" -ArgumentList @("purge", "--confirm-command") `
    -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$outputPath/uninstall.out" `
    -RedirectStandardError "$outputPath/uninstall.err"
if ($p.ExitCode -ne 0 -or (Test-Path "$root/bin/PlotJuggler4.exe")) { throw "Uninstall failed" }
$after = (Get-FileHash $installer[0].FullName -Algorithm SHA256).Hash.ToLower()
if ($before -ne $after) { throw "Original installer changed during acceptance" }
