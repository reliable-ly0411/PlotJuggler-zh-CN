# SPDX-License-Identifier: MPL-2.0
param([string]$Packages = "pkg", [string]$Output = "reports",
      [ValidateSet("ifw", "portable")][string]$Format = "ifw")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $Output | Out-Null
$outputPath = (Resolve-Path $Output).Path
# Validate every original Windows asset, matching both its name and full digest.
$checksums = @{}
foreach ($line in Get-Content (Join-Path $Packages "SHA256SUMS-Windows.txt")) {
    if ($line -notmatch '^([a-f0-9]{64})  ([^/\\]+)$') { throw "Invalid checksum entry" }
    $name = $Matches[2]
    if ($checksums.ContainsKey($name)) { throw "Duplicate checksum entry: $name" }
    $checksums[$name] = $Matches[1]
}
$assets = @(Get-ChildItem $Packages -File | Where-Object { $_.Extension -in @('.exe', '.zip') })
if ($assets.Count -ne 2 -or $checksums.Count -ne 2) { throw "Require installer and portable checksums" }
foreach ($asset in $assets) {
    if ((Get-FileHash $asset.FullName -Algorithm SHA256).Hash.ToLower() -ne $checksums[$asset.Name]) {
        throw "Downloaded package checksum mismatch: $($asset.Name)"
    }
}
$extension = if ($Format -eq 'portable') { '.zip' } else { '.exe' }
$package = @($assets | Where-Object { $_.Extension -eq $extension })
if ($package.Count -ne 1) { throw "Expected exactly one $Format package" }
$root = Join-Path $env:RUNNER_TEMP ("pj4-" + $Format + "-" + [guid]::NewGuid())
if ($Format -eq 'portable') {
    # This job has no IFW installation or build payload. Launch only ZIP contents.
    [System.IO.Compression.ZipFile]::ExtractToDirectory($package[0].FullName, $root)
    if (Test-Path "$root/maintenancetool.exe") { throw "Unexpected IFW installation in portable ZIP" }
} else {
    $p = Start-Process $package[0].FullName -ArgumentList @("install", "--root", "`"$root`"",
        "--accept-licenses", "--default-answer", "--confirm-command") -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput (Join-Path $outputPath 'installer.out') `
        -RedirectStandardError (Join-Path $outputPath 'installer.err')
    if ($p.ExitCode -ne 0) { throw "Final installer failed: $($p.ExitCode)" }
    [xml]$components = Get-Content (Join-Path $root "components.xml")
    $installed = ($components.Packages.Package | Where-Object { $_.Name -eq "io.plotjuggler.application" }).Version
    $release = Get-Content (Join-Path $root "share/plotjuggler4/release.json") -Raw | ConvertFrom-Json
    if ($installed -ne $release.ifw_package_version) { throw "IFW version mismatch" }
}
$version = (Get-Content versions.env | Where-Object { $_ -match "^PJ_APP_VERSION=" }) -replace "^PJ_APP_VERSION=", ""
$python = (Get-Command python).Source
foreach ($key in @('QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'QT_QPA_FONTDIR', 'PYTHONHOME', 'PYTHONPATH', 'LD_LIBRARY_PATH')) {
    Remove-Item "Env:$key" -ErrorAction SilentlyContinue
}
$env:PATH = "$root/bin;$env:SystemRoot/System32;$env:SystemRoot"
& $python -X utf8 scripts/verify_windows_application.py "$root/bin/PlotJuggler4.exe" --runtime --expected-version $version
if ($LASTEXITCODE -ne 0) { throw "Installed Windows executable verification failed" }
& $python -X utf8 packaging/localization/verify_package.py --prefix $root --executable "$root/bin/PlotJuggler4.exe" `
    --real-bin 3rdparty/plotjuggler-apbin-plugins/tests/logs/00000001.BIN --output "$outputPath/runtime" --expected-source $env:GITHUB_SHA --expected-version $version --capture
if ($LASTEXITCODE -ne 0) { throw "Installed package acceptance failed" }
if ($Format -eq 'ifw') {
    $p = Start-Process "$root/maintenancetool.exe" -ArgumentList @("purge", "--confirm-command") `
        -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$outputPath/uninstall.out" `
        -RedirectStandardError "$outputPath/uninstall.err"
    if ($p.ExitCode -ne 0 -or (Test-Path "$root/bin/PlotJuggler4.exe")) { throw "Uninstall failed" }
}
foreach ($asset in $assets) {
    $after = (Get-FileHash $asset.FullName -Algorithm SHA256).Hash.ToLower()
    if ($checksums[$asset.Name] -ne $after) { throw "Original package changed during acceptance: $($asset.Name)" }
}
@{ format = $Format; name = $package[0].Name; before = $checksums[$package[0].Name];
   after = (Get-FileHash $package[0].FullName -Algorithm SHA256).Hash.ToLower() } |
    ConvertTo-Json | Set-Content -Encoding utf8 "$outputPath/runtime/package-integrity.json"
