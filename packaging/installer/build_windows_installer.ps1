<#
.SYNOPSIS
  Build the PlotJuggler 4 Windows installer (Qt Installer Framework, offline).

.DESCRIPTION
  Stages the already-built pj_app.exe plus its runtime dependencies into a
  scratch packages tree, then runs binarycreator to produce one self-contained
  .exe. The source packages directory (packaging/installer/packages/) is NOT mutated by
  this script — everything is staged under $env:TEMP so a build never dirties
  the working tree.

    1. locate the built pj_app.exe under -BuildDir
    2. stage it under <stage>/packages/io.plotjuggler.application/data/bin/PlotJuggler4.exe
    3. resolve the curated plugin ids from pj-plugin-registry (unless
       -SkipPlugins), verify each published ZIP's SHA-256, and unpack it into
       data/lib/plotjuggler/plugins
    4. windeployqt the exe AND every bundled plugin DLL — matches PJ3 (a plugin can
       pull Qt modules the main exe does not)
    5. copy the FFmpeg + CPython + other Conan-shared runtime DLLs from the
       Conan cache that produced the build (constrained to package bin dirs)
    6. load every whitelisted plugin through the staged app and require an exact
       id/version match with no loader errors
    7. render config.xml / package.xml from templates into the stage tree
    8. binarycreator --offline-only -> PlotJuggler-<Version>-Windows-x64.exe
       (or, without -CleanReleaseName, PlotJuggler-<Version>-Windows-x64.<short-commit>.exe)

  This does NOT build the app or any plugins. Run it AFTER a Windows build of
  the app, e.g.
    conan install . --output-folder=build --build=missing \
        -s build_type=RelWithDebInfo -s compiler.cppstd=20 \
        -o "cpython/*:shared=True" -s "cpython/*:build_type=Release"
    cmake --preset ... && cmake --build build --config RelWithDebInfo

.PARAMETER BuildDir
  The PJ4 build directory (default: build). Searched for plotjuggler4.exe /
  pj_app.exe under RelWithDebInfo/ (preferred) then Release/.

.PARAMETER QtDir
  Qt kit dir that owns windeployqt.exe, e.g. C:\Qt\6.11.1\msvc2022_64.
  If empty, windeployqt is taken from PATH.

.PARAMETER IfwDir
  Directory containing binarycreator.exe and installerbase.exe (IFW >=4.10).
  Explicit paths never fall back. If empty, reuse pinned tools or discover PATH /
  Qt tools; if missing or too old, fetch the official hash-verified 4.10 tools.

.PARAMETER SkipPlugins
  Skip downloading/bundling plugins for a fast core-only installer.

.PARAMETER PluginRegistryUrl
  Registry JSON URL (or local JSON path) used to resolve published plugin
  artifacts. Defaults to the development registry used by the marketplace.

.PARAMETER PluginIds
  Registry extension ids to bundle. Every requested id must have a valid artifact
  for -PluginPlatform; a missing entry, failed download, bad checksum, or malformed
  archive fails the installer build.

.PARAMETER PluginPlatform
  Registry platform key. The x64 Windows installer uses windows-x86_64.

.PARAMETER ConanHome
  Legacy cache-root diagnostic label. Runtime DLL selection is restricted to
  the active host nodes in BuildDir/conan-graph.json.

.PARAMETER Version
  Installer version string, also used in the output file name. Default reads
  PJ_APP_VERSION from repo-root versions.env when present, otherwise falls
  back to the value hard-coded here.

.PARAMETER OutDir
  Where to write the installer .exe (default: current directory).

.PARAMETER CleanReleaseName
  Name the output PlotJuggler-<Version>-Windows-x64.exe instead of the default
  commit-stamped name, matching the Linux AppImage's plain
  PlotJuggler-<version>-<arch>.AppImage naming. Use for tag-triggered releases,
  where -Version is already the unique identifier; leave off for
  workflow_dispatch/dev builds, where the built commit's short hash
  disambiguates otherwise-identical-looking artifacts.

.PARAMETER StageDir
  Scratch directory for the staged package tree (default: $env:TEMP\pj4-installer-stage).
  Wiped at the start of every run.

.PARAMETER UpdateUrl
  Publish the installer with remote updates enabled, pointing the installed
  maintenance tool at this repository URL (e.g. https://apt.plotjuggler.io/windows).
  Omit it and the installer behaves exactly as before: the maintenance tool
  only uninstalls.

  This URL is compiled into the maintenance tool at INSTALL time, so it only
  ever reaches machines that installed a build which already carried it —
  turning it on does nothing for anyone who installed an earlier release.

.PARAMETER RepoOutDir
  Also run repogen over the same staged packages tree and write an IFW update
  repository here (wiped first). This is what -UpdateUrl points at once
  published; the two are set together in a release.

.NOTES
  Host requirements:
    - Qt 6.11.1 msvc2022_64 (windeployqt.exe) -- auto-found in .qt when present
    - Qt Installer Framework tools (binarycreator.exe) -- install via the Qt
      Maintenance Tool, or:  aqt install-tool --outputdir .qt windows desktop tools_ifw
    - A populated Conan cache from the PJ4 build (FFmpeg + CPython DLLs)
    - Network access to the plugin registry and its published artifacts (unless
      -SkipPlugins or -PluginRegistryUrl points to a local registry mirror)
#>
param(
  [string]$BuildDir   = "build",
  [string]$QtDir      = "",
  [string]$IfwDir     = "",
  [switch]$SkipPlugins,
  [string]$PluginRegistryUrl = "https://raw.githubusercontent.com/PlotJuggler/pj-plugin-registry/refs/heads/development/registry.json",
  [string[]]$PluginIds = @(
    "mcap-loader", "csv-loader", "parquet-loader", "ulog-loader",
    "mp4-loader", "pointcloud-3d-loader",
    "dummy-streamer", "foxglove-bridge", "plotjuggler-bridge", "webrtc-client",
    "ros-parser", "protobuf-parser", "json-parser", "data-tamer-parser",
    "toolbox-quaternion", "toolbox-transform-editor", "toolbox-mosaico",
    "arrow-parser"
  ),
  [string]$PluginPlatform = "windows-x86_64",
  [string]$ConanHome  = "$env:USERPROFILE\.conan2",
  [string]$Version    = "",
  [string]$OutDir     = ".",
  [string]$StageDir   = "",
  [switch]$CleanReleaseName,
  [string]$UpdateUrl  = "",
  [string]$RepoOutDir = "",
  [string]$ExtraPrefix = "",
  [string]$NameSuffix = "-zh-CN",
  [string]$PackageVersion = ""
)

$ErrorActionPreference = "Stop"
function Info($m)  { Write-Host "[installer] $m" -ForegroundColor Cyan }
function Warn($m)  { Write-Host "[installer] WARNING: $m" -ForegroundColor Yellow }
function Die($m)   { Write-Host "[installer] ERROR: $m" -ForegroundColor Red; exit 1 }

$installerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path      # ...\packaging\installer
$repoRoot      = Split-Path -Parent (Split-Path -Parent $installerRoot)
$pkgSrc        = Join-Path $installerRoot "packages\io.plotjuggler.application"
$configXmlSrc  = Join-Path $installerRoot "config.xml"
$packageXmlSrc = Join-Path $pkgSrc        "meta\package.xml"

# --- default version from versions.env -------------------------------------
if (-not $Version) {
  $versionsEnv = Join-Path $repoRoot "versions.env"
  if (Test-Path $versionsEnv) {
    $line = Get-Content $versionsEnv | Where-Object { $_ -match '^\s*PJ_APP_VERSION\s*=\s*(.+?)\s*$' } | Select-Object -First 1
    if ($line -and $Matches[1]) { $Version = $Matches[1] }
  }
}
if (-not $Version) { $Version = "3.999.1" }  # last-resort fallback
Info "target version: $Version"

# --- stage directory (scratch, wiped on every run) ------------------------
if (-not $StageDir) { $StageDir = Join-Path $env:TEMP "pj4-installer-stage" }
if (Test-Path $StageDir) { Remove-Item $StageDir -Recurse -Force }
$stagePackages = Join-Path $StageDir "packages"
$stagePkgRoot  = Join-Path $stagePackages "io.plotjuggler.application"
$stageMeta     = Join-Path $stagePkgRoot "meta"
$stageData     = Join-Path $stagePkgRoot "data"
# Prefix layout the installed app expects: <prefix>/bin holds the exe + all its
# runtime DLLs; plugins live in <prefix>/lib/plotjuggler/plugins, which the app
# resolves relative to the exe (bin -> ../lib/plotjuggler/plugins) and scans
# recursively. config.xml's TargetDir is <prefix>; $stageData maps to it.
$stageBin      = Join-Path $stageData "bin"
$stagePlugins  = Join-Path $stageData "lib\plotjuggler\plugins"
New-Item -ItemType Directory -Force -Path $stageMeta,$stageBin,$stagePlugins | Out-Null
Info "stage: $StageDir"

# --- resolve tools ---------------------------------------------------------
function Resolve-Exe([string]$name, [string]$hintDir) {
  if ($hintDir -and (Test-Path (Join-Path $hintDir $name))) { return (Join-Path $hintDir $name) }
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}

# Default -QtDir to the aqt layout inside the repo (.qt) when present, so a machine
# that installed Qt via scripts/install_qt6.sh / aqt needs no -QtDir.
if (-not $QtDir) {
  $qtGuess = Join-Path $repoRoot ".qt\6.11.1\msvc2022_64"
  if (Test-Path (Join-Path $qtGuess "bin\windeployqt.exe")) { $QtDir = $qtGuess; Info "auto-detected Qt: $QtDir" }
}
$qtBinDir = if ($QtDir) { Join-Path $QtDir "bin" } else { "" }
$windeployqt = Resolve-Exe "windeployqt.exe" $qtBinDir
if (-not $windeployqt) { Die "windeployqt.exe not found. Pass -QtDir <kit> (e.g. .qt\6.11.1\msvc2022_64 or C:\Qt\6.11.1\msvc2022_64) or add it to PATH." }
Info "windeployqt : $windeployqt"

# binarycreator and repogen ship in the same IFW bin directory, so one search
# serves both.
function Resolve-IfwTool([string]$name) {
  # An explicit tool directory is a boundary, not a discovery hint.
  if ($IfwDir) {
    $explicit = Join-Path $IfwDir $name
    if (Test-Path $explicit) { return $explicit }
    return $null
  }
  $pinned = Join-Path $repoRoot ".qt/Tools/QtInstallerFramework/4.10.0-pinned/bin/$name"
  if (Test-Path $pinned) { return $pinned }
  $found = Resolve-Exe $name ""
  if ($found) { return $found }
  # Search the usual IFW-tool locations. aqt lays them under <aqt-base>\Tools\
  # QtInstallerFramework, where <aqt-base> is two levels above the kit dir
  # (e.g. .qt\6.11.1\msvc2022_64 -> .qt); the Qt online installer uses C:\Qt\Tools.
  $ifwRoots = @()
  if ($QtDir) {
    $aqtBase = Split-Path -Parent (Split-Path -Parent $QtDir)
    if ($aqtBase) { $ifwRoots += (Join-Path $aqtBase "Tools\QtInstallerFramework") }
  }
  $ifwRoots += "C:\Qt\Tools\QtInstallerFramework"
  foreach ($root in $ifwRoots) {
    if (-not (Test-Path $root)) { continue }
    $cand = Get-ChildItem $root -Recurse -Filter $name -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1
    if ($cand) { return $cand.FullName }
  }
  return $null
}

# binarycreator has no --version option. installerbase handles this CLI option
# before loading package metadata (IFW src/sdk/main.cpp).
function Get-IfwVersion([string]$creator) {
  if (-not $creator) { return $null }
  $installerbase = Join-Path (Split-Path $creator -Parent) "installerbase.exe"
  if (-not (Test-Path $installerbase)) { return $null }
  try {
    $output = (& $installerbase --version 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { return $null }
    if ($output -match 'IFW Version:\s+(\d+\.\d+\.\d+)(?:,|\s|$)') {
      return [version]$Matches[1]
    }
  } catch {
    Warn "Could not query IFW runtime: $_"
  }
  return $null
}

$binarycreator = Resolve-IfwTool "binarycreator.exe"
$ifwVersion = Get-IfwVersion $binarycreator
if (-not $ifwVersion -or $ifwVersion -lt [version]'4.10.0') {
  if ($IfwDir) {
    Die "Explicit -IfwDir requires Qt Installer Framework 4.10.0 or newer with a working installerbase.exe. It will not be replaced or bypassed: $IfwDir"
  }
  Info "No compatible default IFW found; fetching verified official IFW 4.10.0 tools."
  try {
    $IfwDir = & (Join-Path $installerRoot "install_ifw.ps1")
  } catch {
    Die "Official IFW setup failed; no fallback will be used. Install IFW 4.10 or newer manually and pass -IfwDir <bin>: $_"
  }
  $binarycreator = Resolve-IfwTool "binarycreator.exe"
  $ifwVersion = Get-IfwVersion $binarycreator
  if (-not $ifwVersion -or $ifwVersion -lt [version]'4.10.0') { Die "Verified IFW setup did not yield a compatible runtime." }
}
# Keep repogen and binarycreator from the same validated tool installation.
$IfwDir = Split-Path $binarycreator -Parent
Info "binarycreator: $binarycreator (IFW $ifwVersion)"

# Resolved up front, not after the long staging run: a missing repogen should
# fail in the first seconds, not after windeployqt and the plugin downloads.
$repogen = ""
if ($RepoOutDir) {
  $repogen = Resolve-IfwTool "repogen.exe"
  if (-not $repogen) { Die "repogen.exe not found, but -RepoOutDir was given. It ships beside binarycreator in the Qt Installer Framework tools." }
  Info "repogen      : $repogen"
}

# --- locate the built app --------------------------------------------------
# Prefer RelWithDebInfo (CI default), then Release, then any config. The CMake
# target 'pj_app' has OUTPUT_NAME plotjuggler4 on main, but older builds still
# ship as pj_app.exe — accept either.
function Find-AppExe {
  foreach ($cfg in @("RelWithDebInfo","Release","*")) {
    foreach ($name in @("plotjuggler4.exe","pj_app.exe")) {
      $glob = if ($cfg -eq "*") { $name } else { "$cfg\$name" }
      $hit = Get-ChildItem -LiteralPath $BuildDir -Recurse -Filter $name -ErrorAction SilentlyContinue |
             Where-Object { $_.FullName -like "*\$glob" -or $cfg -eq "*" } |
             Sort-Object LastWriteTime -Descending | Select-Object -First 1
      if ($hit) { return $hit }
    }
  }
  return $null
}
$appExe = Find-AppExe
if (-not $appExe) { Die "plotjuggler4.exe / pj_app.exe not found under '$BuildDir'. Build PJ4 first (cmake --build build --config RelWithDebInfo)." }
Info "app binary  : $($appExe.FullName)"

# --- stage the data payload ------------------------------------------------
$stagedExe = Join-Path $stageBin "PlotJuggler4.exe"
Copy-Item $appExe.FullName $stagedExe
Info "staged bin\PlotJuggler4.exe"

# The marketplace runs the first dlopen of a downloaded plugin inside
# pj-plugin-check rather than in the application process. ExtensionManager fails
# closed when the helper cannot be started, so an installer that omits it rejects
# every marketplace install. The helper must sit in the same directory as the
# application: the SDK opens plugin DLLs with LOAD_LIBRARY_SEARCH_DEFAULT_DIRS,
# which resolves their dependent DLLs against the loading executable's directory.
# It links no Qt, so windeployqt is not run over it.
$helperExe = Join-Path $appExe.Directory.FullName "pj-plugin-check.exe"
if (-not (Test-Path $helperExe)) {
  Die "pj-plugin-check.exe not found next to '$($appExe.FullName)'. Build the pj-plugin-check target first; without it the packaged app rejects every marketplace install."
}
Copy-Item $helperExe (Join-Path $stageBin "pj-plugin-check.exe")
Info "staged bin\pj-plugin-check.exe"

# --- download published plugins from pj-plugin-registry ---------------------------
# Plugin release ZIPs are the same marketplace artifacts the Linux AppImage bundles.
# They carry the plugin DLL + embedded-manifest sidecar and statically link their
# non-Qt dependencies, so the installer only needs to verify and unpack them.
function Read-PluginRegistry([string]$source) {
  try {
    if ($source -match '^[a-zA-Z][a-zA-Z0-9+.-]*://') {
      $remoteRegistry = Invoke-RestMethod -Uri $source
      return $remoteRegistry
    }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
      Die "plugin registry not found: $source"
    }
    $localRegistry = Get-Content -LiteralPath $source -Raw | ConvertFrom-Json
    return $localRegistry
  } catch {
    Die "failed to read plugin registry '$source': $_"
  }
}

function Download-RegistryPlugins {
  Info "fetching plugin registry: $PluginRegistryUrl"
  $registry = Read-PluginRegistry $PluginRegistryUrl
  if (-not $registry -or -not $registry.extensions) {
    Die "plugin registry has no 'extensions' array: $PluginRegistryUrl"
  }

  $downloadRoot = Join-Path $StageDir "plugin-downloads"
  New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
  $seen = @{}

  foreach ($id in $PluginIds) {
    if ($id -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
      Die "invalid plugin registry id '$id'"
    }
    if ($seen.ContainsKey($id)) { Die "duplicate plugin registry id '$id'" }
    $seen[$id] = $true

    $registryMatches = @($registry.extensions | Where-Object { $_.id -eq $id })
    if ($registryMatches.Count -ne 1) {
      Die "plugin registry must contain exactly one '$id' entry (found $($registryMatches.Count))"
    }
    $extension = $registryMatches[0]
    $extensionVersion = [string]$extension.version
    if (-not $extensionVersion) { Die "plugin '$id' has an empty registry version" }
    $platformProperty = $extension.platforms.PSObject.Properties[$PluginPlatform]
    if (-not $platformProperty) {
      Die "plugin '$id' has no '$PluginPlatform' artifact in the registry"
    }
    $artifact = $platformProperty.Value
    $url = [string]$artifact.url
    $checksum = [string]$artifact.checksum
    if (-not $url) { Die "plugin '$id' has an empty '$PluginPlatform' URL" }
    $checksumMatch = [regex]::Match($checksum, '^sha256:([0-9a-fA-F]{64})$')
    if (-not $checksumMatch.Success) {
      Die "plugin '$id' has an invalid SHA-256 checksum: '$checksum'"
    }
    $expectedHash = $checksumMatch.Groups[1].Value.ToLowerInvariant()

    $zipPath = Join-Path $downloadRoot "$id.zip"
    Info "downloading plugin: $id $($extension.version)"
    try {
      Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    } catch {
      Die "failed to download plugin '$id' from '$url': $_"
    }
    $actualHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $expectedHash) {
      Die "checksum mismatch for plugin '$id' (want $expectedHash, got $actualHash)"
    }

    $unpackDir = Join-Path $downloadRoot "unpacked-$id"
    New-Item -ItemType Directory -Force -Path $unpackDir | Out-Null
    try {
      Expand-Archive -LiteralPath $zipPath -DestinationPath $unpackDir -Force
    } catch {
      Die "failed to unpack plugin '$id': $_"
    }

    # Official archives have one top-level <id>/ directory. Normalize that away
    # so the installed layout is always plugins/<id>/{manifest.json,*_plugin.dll}.
    $entries = @(Get-ChildItem -LiteralPath $unpackDir -Force)
    $payloadRoot = $unpackDir
    if ($entries.Count -eq 1 -and $entries[0].PSIsContainer) {
      $payloadRoot = $entries[0].FullName
    }
    $destination = Join-Path $stagePlugins $id
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Get-ChildItem -LiteralPath $payloadRoot -Force |
      Copy-Item -Destination $destination -Recurse -Force

    $downloadedDlls = @(Get-ChildItem -LiteralPath $destination -Recurse -Filter "*_plugin.dll")
    if ($downloadedDlls.Count -eq 0) {
      Die "plugin '$id' archive contains no *_plugin.dll"
    }
    $manifests = @(Get-ChildItem -LiteralPath $destination -Recurse -Filter "manifest.json")
    if ($manifests.Count -ne 1) {
      Die "plugin '$id' archive must contain exactly one manifest.json (found $($manifests.Count))"
    }
    try {
      $packageManifest = Get-Content -LiteralPath $manifests[0].FullName -Raw | ConvertFrom-Json
    } catch {
      Die "plugin '$id' contains an invalid manifest.json: $_"
    }
    if ([string]$packageManifest.id -ne $id) {
      Die "plugin '$id' archive manifest declares id '$($packageManifest.id)'"
    }
    if ([string]$packageManifest.version -ne $extensionVersion) {
      Die "plugin '$id' archive version '$($packageManifest.version)' does not match registry version '$extensionVersion'"
    }
    # Admission follows the host's SDK/ABI contract, not the deprecated app
    # display-version hint. The staged executable validates every plugin below.
    $resolvedPluginVersions[$id] = $extensionVersion
    Info "staged plugin: $id ($($downloadedDlls.Count) DLL(s))"
  }

  return @(Get-ChildItem -LiteralPath $stagePlugins -Recurse -Filter "*_plugin.dll" |
            Sort-Object FullName)
}

$resolvedPluginVersions = @{}
$pluginDlls = @()
if ($SkipPlugins) {
  Info "skipping plugins (-SkipPlugins) -> core-only installer"
} else {
  $pluginDlls = @(Download-RegistryPlugins)
  Info "staged $($pluginDlls.Count) plugin DLL(s) from $($PluginIds.Count) registry extension(s)"
}

# Merge the pinned fork payload before validating the sealed runtime closure.
if ($ExtraPrefix) {
  if (-not (Test-Path -LiteralPath $ExtraPrefix -PathType Container)) { Die "extra prefix missing: $ExtraPrefix" }
  python (Join-Path $PSScriptRoot "../localization/replace_localized_plugins.py") --extra-prefix $ExtraPrefix --destination $stageData
  if ($LASTEXITCODE -ne 0) { Die "localized plugin replacement failed" }
  Get-ChildItem -LiteralPath $ExtraPrefix -Force | Copy-Item -Destination $stageData -Recurse -Force
  $extraManifest = Join-Path $stagePlugins "ardupilot-dataflash\manifest.json"
  $m = Get-Content -LiteralPath $extraManifest -Raw | ConvertFrom-Json
  if ($m.id -ne "ardupilot-dataflash") { Die "unexpected fork plugin id" }
  $resolvedPluginVersions[$m.id] = [string]$m.version
  $PluginIds += [string]$m.id
  $pluginDlls = @(Get-ChildItem -LiteralPath $stagePlugins -Recurse -Filter "*_plugin.dll" | Sort-Object FullName)
}
if (-not $PackageVersion) { $PackageVersion = $Version }
if ($PackageVersion -notmatch '^[0-9]+((\.|-)[0-9]+)*$') { Die "IFW requires a numeric PackageVersion" }

# --- Qt deployment (Qt DLLs + Qt plugins + MSVC runtime) -------------------
# windeployqt has to be run over the exe AND every plugin DLL: a plugin can
# pull Qt modules (Qt Charts, Qt SVG, Qt QuickWidgets …) the main exe does
# not, and without walking each plugin those transitive Qt DLLs never land in
# the bundle — the classic "window doesn't render fully" symptom.
Info "running windeployqt on exe + plugins ..."
& $windeployqt --release --no-translations --compiler-runtime $stagedExe
if ($LASTEXITCODE -ne 0) { Die "windeployqt failed on the exe (exit $LASTEXITCODE)." }
# Only the bundled plugin DLLs — NOT every DLL in data\, which by now also holds the
# non-Qt files windeployqt itself dropped (D3Dcompiler_47.dll, opengl32sw.dll, …);
# running windeployqt over those makes it exit 1. Empty when -SkipPlugins.
foreach ($d in $pluginDlls) {
  # --dir $stageBin: the plugin lives under lib\..., but its extra Qt module DLLs
  # must land in bin\ next to the exe (the dir Windows searches at load time), not
  # next to the plugin — otherwise a plugin-only Qt module never resolves.
  & $windeployqt --dir $stageBin --release --no-translations $d.FullName
  # Warn, don't Die: a recursively-collected DLL that is not a Qt-linked plugin
  # makes windeployqt exit 1, which must not abort the whole bundle.
  if ($LASTEXITCODE -ne 0) { Warn "windeployqt on $($d.Name) returned $LASTEXITCODE -- harmless if it is not a Qt-linked plugin." }
}

# App-local MSVC runtime avoids depending on a preinstalled redistributable.
# VCToolsRedistDir is supplied by the selected official MSVC toolchain.
$crt = Join-Path $env:VCToolsRedistDir "x64\Microsoft.VC143.CRT"
if (-not (Test-Path $crt)) { Die "MSVC app-local runtime not found: $crt" }
Get-ChildItem $crt -Filter "*.dll" | Copy-Item -Destination $stageBin -Force
foreach ($name in @("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll")) {
  if (-not (Test-Path (Join-Path $stageBin $name))) { Die "missing app-local MSVC runtime: $name" }
}

# --- copy non-Qt runtime DLLs from the Conan cache -------------------------
# windeployqt only knows about Qt; Conan-shared deps are copied by hand.
#
# Constrain the active graph to Conan 2 package "bin" folders: both the downloaded
# layout (~/.conan2/p/<hash>/p/bin) and the built-from-source layout
# (~/.conan2/p/b/<hash>/p/bin, note the extra "b" segment). WITHOUT that
# constraint the recursive scan also picks up copies under a package's build
# tree (~/.conan2/p/b/<hash>/build/...), the "newest by mtime" may be one of
# those, and the sibling DLL copy pulls unrelated intermediates.
# Only package directories in this build's resolved graph are eligible.
$graphPath = Join-Path $BuildDir "conan-graph.json"
$graph = Get-Content -LiteralPath $graphPath -Raw | ConvertFrom-Json
$runtimeDirs = @($graph.graph.nodes.PSObject.Properties.Value |
  Where-Object { $_.package_folder -and $_.context -eq "host" } |
  ForEach-Object { Join-Path $_.package_folder "bin" } |
  Where-Object { Test-Path -LiteralPath $_ } | Sort-Object -Unique)
if ($runtimeDirs.Count -eq 0) { Die "No active package runtime directories in $graphPath" }
function Copy-ConanRuntime([string]$probeDll, [string]$label, [switch]$Required) {
  $hit = Get-ChildItem -LiteralPath $runtimeDirs -Filter $probeDll -ErrorAction SilentlyContinue |
         Where-Object { $_.FullName -match '\\p\\(?:b\\)?[^\\]+\\p\\bin\\' } |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $hit) {
    if ($Required) { Die "$label runtime not found in Conan cache ($ConanHome\p\[b\]*\p\bin\$probeDll). Was the build done with this cache?" }
    Warn "$label runtime ($probeDll) not found in Conan cache -- skipping (bundle it manually if the app needs it)."
    return
  }
  $srcDir = $hit.Directory.FullName
  $copied = 0
  foreach ($d in (Get-ChildItem -LiteralPath $srcDir -Filter "*.dll")) { Copy-Item -LiteralPath $d.FullName -Destination $stageBin -Force; $copied++ }
  Info "staged $copied $label DLL(s) from $srcDir"
}

Copy-ConanRuntime "avcodec*.dll" "FFmpeg"     -Required
Copy-ConanRuntime "python3*.dll" "CPython"    -Required
Copy-ConanRuntime "dav1d*.dll"   "libdav1d"           # AV1 decode via FFmpeg
Copy-ConanRuntime "draco*.dll"   "Draco"               # compressed pointcloud decode
Copy-ConanRuntime "zstd*.dll"    "zstd"
Copy-ConanRuntime "lz4*.dll"     "LZ4"
Copy-ConanRuntime "mcap*.dll"    "mcap"

# CPython needs its stdlib next to the DLL for the embedded interpreter to
# initialise. Copy Lib/, DLLs/ and any python3XX._pth from the same Conan
# package root as the python3XX.dll we just staged.
function Copy-CPythonStdlib {
  $pyDll = Get-ChildItem -LiteralPath $runtimeDirs -Filter "python312.dll" -ErrorAction SilentlyContinue |
           Where-Object { $_.FullName -match '\\p\\(?:b\\)?[^\\]+\\p\\bin\\' } |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $pyDll) { Warn "CPython DLL missing -- stdlib bundling skipped."; return }
  # On Windows the Conan CPython package nests python3XX.dll, Lib/ (stdlib) and DLLs/
  # TOGETHER under <prefix>/bin — i.e. the stdlib lives in the DLL's OWN directory
  # (pj_scripting points PYTHONHOME there too). Look there, not one level up.
  $pyBin = $pyDll.Directory.FullName
  foreach ($sub in @("Lib", "DLLs")) {
    $src = Join-Path $pyBin $sub
    if (Test-Path -LiteralPath $src) {
      Copy-Item -LiteralPath $src -Destination $stageBin -Recurse -Force
      Info "staged CPython $sub/ from $src"
    } elseif ($sub -eq "Lib") {
      Warn "CPython Lib/ not found under $pyBin -- pj_scripting may fail to init the interpreter."
    }
  }
  # A pythonXX._pth next to the DLL makes CPython resolve its stdlib RELATIVE TO THE
  # DLL and ignore PYTHONHOME. That is what makes the interpreter portable: the
  # PJ_PYTHON_HOME baked into the binary is the build machine's Conan cache path,
  # which does not exist on the user's machine. Reuse the package's _pth if it ships
  # one; otherwise synthesize a minimal one named to match the DLL (python312.dll ->
  # python312._pth).
  $pth = Get-ChildItem -LiteralPath $pyBin -Filter "python3*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($pth) {
    Copy-Item -LiteralPath $pth.FullName -Destination $stageBin -Force
    Info "staged $($pth.Name)"
  } else {
    $pthName = [System.IO.Path]::GetFileNameWithoutExtension($pyDll.Name) + "._pth"
    Set-Content -LiteralPath (Join-Path $stageBin $pthName) -Value @(".", "Lib", "DLLs", "import site") -Encoding ASCII
    Info "generated $pthName (portable stdlib path, relative to the DLL)"
  }
}
Copy-CPythonStdlib

# --- prove every whitelisted plugin loads in the staged application ----------------
# Download/checksum success is not sufficient: this exercises the real host loader,
# embedded C-ABI manifest, instance creation/capability probe, dialog-vtable contract,
# and the final staged DLL search path. Missing, extra, wrong-version, or unloadable
# plugins make the release fail before binarycreator runs.
if ($pluginDlls.Count -gt 0) {
  $validationArgs = @("--validate-plugins", $stagePlugins)
  foreach ($id in $PluginIds) {
    $validationArgs += "--expect-plugin"
    $validationArgs += "$id=$($resolvedPluginVersions[$id])"
  }
  Info "validating $($PluginIds.Count) whitelisted plugin(s) with the staged app ..."
  & $stagedExe @validationArgs
  if ($LASTEXITCODE -ne 0) {
    Die "staged plugin validation failed (exit $LASTEXITCODE)"
  }
}

# --- render config.xml + package.xml from source into the stage tree -------
# Templates carry a __PJ_VERSION__ token; the source XMLs stay clean so a
# build never dirties the working tree (the classic "why does my checkout
# look modified" trap).
function Render-Template([string]$src, [string]$dst) {
  (Get-Content -Raw $src) `
    -replace '__PJ_VERSION__', $PackageVersion `
    -replace '__PJ_RELEASE_DATE__', (Get-Date -Format 'yyyy-MM-dd') |
    Set-Content $dst
}
Render-Template $configXmlSrc  (Join-Path $StageDir "config.xml")
Render-Template $packageXmlSrc (Join-Path $stageMeta "package.xml")

# --- remote updates (optional) ---------------------------------------------
# Injected here rather than templated into config.xml so that a build without
# -UpdateUrl stays byte-identical to one from before this existed: an empty
# <Url/> would leave every maintenance tool polling nothing on each launch.
if ($UpdateUrl) {
  $cfgPath = Join-Path $StageDir "config.xml"
  $closing = "</Installer>"
  $cfg = (Get-Content -Raw $cfgPath).TrimEnd()
  if (-not $cfg.EndsWith($closing)) { Die "config.xml does not end with $closing; cannot inject the update repository." }
  # Built by concatenation rather than -replace: a URL is substituted verbatim
  # here, while -replace would read a '$' in it as a capture-group reference.
  $block = @"

  <RemoteRepositories>
    <Repository>
      <Url>$UpdateUrl</Url>
      <Enabled>1</Enabled>
      <DisplayName>PlotJuggler 4 updates</DisplayName>
    </Repository>
  </RemoteRepositories>
$closing
"@
  Set-Content $cfgPath ($cfg.Substring(0, $cfg.Length - $closing.Length).TrimEnd() + $block)
  Info "remote updates: $UpdateUrl"
}

# Non-templated meta files (script, UI, licenses) go verbatim.
foreach ($f in Get-ChildItem (Join-Path $pkgSrc "meta") -File | Where-Object { $_.Name -ne "package.xml" }) {
  Copy-Item $f.FullName $stageMeta -Force
}

# Compile the component catalog with the same pinned Qt kit as the application.
$lrelease = Resolve-Exe "lrelease.exe" (Split-Path $windeployqt -Parent)
if (-not $lrelease) { Die "lrelease.exe not found. Install Qt Linguist tools in the selected kit or add them to PATH." }

# Explicit resources are required: IFW's SDK wildcard omits zh_CN catalogs.
$translationStage = Join-Path $StageDir "translations"
New-Item -ItemType Directory -Force -Path $translationStage | Out-Null
# IFW 4.10 component catalogs follow the OS locale, not --lang. Merge the
# custom context into the catalog selected by the SDK --lang path instead.
& $lrelease (Join-Path $installerRoot "translations/ifw_zh_CN.ts") (Join-Path $stageMeta "zh_CN.ts") -qm (Join-Path $translationStage "ifw_zh_CN.qm")
if ($LASTEXITCODE -ne 0) { Die "IFW standard-page translation compilation failed." }
$qtChinese = Join-Path (Split-Path (Split-Path $windeployqt -Parent) -Parent) "translations/qtbase_zh_CN.qm"
if (-not (Test-Path $qtChinese)) { Die "Missing Qt Base Chinese translation: $qtChinese" }
Copy-Item $qtChinese (Join-Path $translationStage "qt_zh_CN.qm")
$translationQrc = Join-Path $translationStage "translations.qrc"
@'
<RCC><qresource prefix="/translations_new">
  <file>ifw_zh_CN.qm</file>
  <file>qt_zh_CN.qm</file>
</qresource></RCC>
'@ | Set-Content -Encoding UTF8 $translationQrc
$ifwLicenseDir = Join-Path $stageData "share/licenses/QtInstallerFramework"
New-Item -ItemType Directory -Force -Path $ifwLicenseDir | Out-Null
Copy-Item (Join-Path $installerRoot "translations/LICENSE.GPL3-EXCEPT") $ifwLicenseDir
Copy-Item (Join-Path $installerRoot "translations/README.md") $ifwLicenseDir

if ($ExtraPrefix) {
  Copy-Item (Join-Path $stageData "share/licenses/Qt-LGPL.txt") (Join-Path $stageMeta "license_lgpl.txt") -Force
}

# --- build the installer ---------------------------------------------------
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Force -Path $OutDir | Out-Null }
if ($CleanReleaseName) {
  # Tag releases: -Version is already the unique identifier, so name the
  # artifact to match the Linux AppImage's plain PlotJuggler-<version>-<arch>.
  $outExe = Join-Path (Resolve-Path $OutDir) "PlotJuggler-$Version-Windows-x64$NameSuffix.exe"
} else {
  # Dev/dispatch builds: stamp with the built commit's short hash so
  # otherwise-identical-looking artifacts stay distinguishable. Matches the
  # AppImage's -commit-hash suffix convention.
  $prevEAP = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  $shortHash = (& git -C $repoRoot rev-parse --short HEAD 2>$null | Select-Object -First 1)
  $ErrorActionPreference = $prevEAP
  if (-not $shortHash) { Die "Could not resolve the built commit's hash in $repoRoot." }
  $shortHash = "$shortHash".Trim()
  $outExe = Join-Path (Resolve-Path $OutDir) "PlotJuggler-$Version-Windows-x64.$shortHash$NameSuffix.exe"
}
Info "running binarycreator -> $outExe"
& $binarycreator --offline-only -r $translationQrc -c (Join-Path $StageDir "config.xml") -p $stagePackages $outExe
if ($LASTEXITCODE -ne 0) { Die "binarycreator failed (exit $LASTEXITCODE)." }

# --- update repository (optional) ------------------------------------------
# Generated from the SAME staged packages tree the installer was just built
# from, so the offline installer and the update repository can never describe
# different payloads for one version.
if ($RepoOutDir) {
  # repogen refuses to write into a populated directory without --update, and
  # a full regeneration is what gets published, so start clean.
  if (Test-Path $RepoOutDir) { Remove-Item $RepoOutDir -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $RepoOutDir | Out-Null
  $repoAbs = (Resolve-Path $RepoOutDir).Path
  Info "running repogen -> $repoAbs"
  & $repogen -p $stagePackages $repoAbs
  if ($LASTEXITCODE -ne 0) { Die "repogen failed (exit $LASTEXITCODE)." }
  $updatesXml = Join-Path $repoAbs "Updates.xml"
  if (-not (Test-Path $updatesXml)) { Die "repogen produced no Updates.xml in $repoAbs." }
  # The version in Updates.xml is what a maintenance tool compares against the
  # installed one; a mismatch here means nobody is ever offered the update.
  if ((Get-Content -Raw $updatesXml) -notmatch [regex]::Escape("<Version>$PackageVersion</Version>")) {
    $found = (Select-String -Path $updatesXml -Pattern '<Version>.*?</Version>' -AllMatches).Matches.Value -join ", "
    Die "Updates.xml advertises [$found], not $Version."
  }
  Info "update repository: $repoAbs"
}

Info "DONE: $outExe"
