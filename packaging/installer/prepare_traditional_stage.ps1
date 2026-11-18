# SPDX-License-Identifier: MPL-2.0
# Experimental #55 stage preparation. Not invoked by release/default builds.
# Use only a disposable, already-staged installer tree; never the source meta.
param(
  [Parameter(Mandatory=$true)][string]$QtBin,
  [Parameter(Mandatory=$true)][string]$StageDir
)
$ErrorActionPreference = 'Stop'
# Resolve against PowerShell's working directory before XML/.NET APIs consume paths.
$QtBin = (Resolve-Path -LiteralPath $QtBin -ErrorAction Stop).ProviderPath
$StageDir = (Resolve-Path -LiteralPath $StageDir -ErrorAction Stop).ProviderPath
$root = $PSScriptRoot
$meta = Join-Path $StageDir 'packages/io.plotjuggler.application/meta'
$translations = Join-Path $StageDir 'translations'
$qrcPath = Join-Path $translations 'translations.qrc'
$lrelease = Join-Path $QtBin 'lrelease.exe'
$qtBase = Join-Path (Split-Path $QtBin -Parent) 'translations/qtbase_zh_TW.qm'
$sourceMeta = Join-Path $root 'packages/io.plotjuggler.application/meta'
if ([IO.Path]::GetFullPath($meta).TrimEnd('/','\') -eq [IO.Path]::GetFullPath($sourceMeta).TrimEnd('/','\')) {
  throw 'Refusing to modify source metadata. Supply a disposable installer stage.'
}
foreach ($path in @($lrelease, $qtBase, $qrcPath, (Join-Path $meta 'languagewidget.ui'), (Join-Path $meta 'installscript.qs'))) {
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing prerequisite: $path" }
}
# Use the version selected by this checkout. Merely finding a different Qt kit
# on disk is not sufficient for reproducible dictionary preparation.
$versions = Get-Content -LiteralPath (Join-Path $root '../../versions.env') -Encoding UTF8
$versionLines = @($versions | Where-Object { $_ -match '^PJ_QT_VERSION=' })
if ($versionLines.Count -ne 1) { throw 'Expected one pinned Qt version' }
$qtVersion = $versionLines[0].Substring('PJ_QT_VERSION='.Length).Trim()
$lreleaseVersion = ((& $lrelease -version 2>&1) | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $lreleaseVersion -notmatch ('(?<![0-9.])' + [regex]::Escape($qtVersion) + '(?![0-9.])')) {
  throw "lrelease does not match pinned Qt $qtVersion"
}
if ((Get-Item -LiteralPath $qtBase).Length -eq 0) { throw 'Empty QtBase Traditional Chinese dictionary' }
$catalogs = @(
  (Join-Path $root 'translations/ifw_zh_TW.ts'),
  (Join-Path $sourceMeta 'zh_TW.ts')
)
$expected = @(700,14)
for ($i=0; $i -lt $catalogs.Count; ++$i) {
  [xml]$ts = Get-Content -LiteralPath $catalogs[$i] -Raw -Encoding UTF8
  $messages = @($ts.SelectNodes('/TS/context/message'))
  if ($ts.TS.language -ne 'zh_TW' -or $messages.Count -ne $expected[$i]) { throw 'Unexpected Traditional Chinese inventory' }
  [xml]$original = Get-Content -LiteralPath (Join-Path (Split-Path $catalogs[$i] -Parent) ([IO.Path]::GetFileName($catalogs[$i]).Replace('zh_TW.ts','zh_CN.ts'))) -Raw -Encoding UTF8
  $originalMessages = @($original.SelectNodes('/TS/context/message'))
  if ($originalMessages.Count -ne $messages.Count) { throw 'Source inventory differs' }
  for ($j=0; $j -lt $messages.Count; ++$j) {
    $message = $messages[$j]
    $source = $originalMessages[$j]
    foreach ($field in @('source','comment')) {
      if ([string]$source.SelectSingleNode($field).InnerText -cne [string]$message.SelectSingleNode($field).InnerText) { throw "Source key differs: $field" }
    }
    if ($source.ParentNode.SelectSingleNode('name').InnerText -cne $message.ParentNode.SelectSingleNode('name').InnerText -or
        $source.GetAttribute('numerus') -cne $message.GetAttribute('numerus')) { throw 'Source context or numerus differs' }
    $translation = $message.SelectSingleNode('translation')
    if ($null -eq $translation -or $translation.GetAttribute('type') -in @('unfinished','obsolete','vanished') -or [string]::IsNullOrWhiteSpace($translation.InnerText)) {
      throw 'Incomplete Traditional Chinese catalog'
    }
    $forms = @($translation.SelectNodes('numerusform'))
    if ($message.GetAttribute('numerus') -eq 'yes') {
      if ($forms.Count -ne 1) { throw 'Traditional Chinese requires one plural form' }
    } elseif ($forms.Count -ne 0) { throw 'Unexpected plural form' }
    foreach ($form in $(if ($forms.Count) { $forms } else { @($translation) })) {
      $pattern = '%(?:L?[1-9][0-9]*|n)'
      $expectedTokens = @([regex]::Matches($source.SelectSingleNode('source').InnerText, $pattern) | ForEach-Object { $_.Value } | Sort-Object)
      $actualTokens = @([regex]::Matches($form.InnerText, $pattern) | ForEach-Object { $_.Value } | Sort-Object)
      if ([string]::IsNullOrWhiteSpace($form.InnerText) -or ($expectedTokens -join '|') -cne ($actualTokens -join '|')) { throw 'Empty translation or placeholder mismatch' }
    }
  }
}
[xml]$ui = Get-Content -LiteralPath (Join-Path $meta 'languagewidget.ui') -Raw -Encoding UTF8
$combo = $ui.SelectSingleNode('//widget[@name="language"]')
if ($null -eq $combo -or @($combo.SelectNodes('item')).Count -ne 2) { throw 'Expected an untouched two-language stage' }
$script = Get-Content -LiteralPath (Join-Path $meta 'installscript.qs') -Raw -Encoding UTF8
if (-not $script.Contains('function installerLanguageForIndex') -or -not $script.Contains('function installerLanguageIndex')) {
  throw 'Stage lacks three-language restart mapping'
}
# Real/synthetic builders substitute only this supervisor payload. An older
# staged script must not be paired with a newer component dictionary.
$sourceScript = Get-Content -LiteralPath (Join-Path $sourceMeta 'installscript.qs') -Raw -Encoding UTF8
$guardPattern = '(?m)^var replacementGuard = "[^"]*";'
$normalizedSource = [regex]::Replace($sourceScript.Replace("`r`n","`n"), $guardPattern, 'var replacementGuard = "STAGED";')
$normalizedStage = [regex]::Replace($script.Replace("`r`n","`n"), $guardPattern, 'var replacementGuard = "STAGED";')
if ($normalizedStage -cne $normalizedSource) { throw 'Staged installer script differs from the selected source' }
[xml]$qrc = Get-Content -LiteralPath $qrcPath -Raw -Encoding UTF8
$resource = $qrc.SelectSingleNode('/RCC/qresource[@prefix="/translations_new"]')
if ($null -eq $resource -or $resource.SelectSingleNode('file[text()="ifw_zh_TW.qm"]')) { throw 'Unexpected or already prepared translation resources' }

# IFW chooses the merged SDK catalog with --lang; component XML alone uses OS
# locale. The QtBase binary must come from the same selected Qt kit, not a
# downloaded unrelated Qt version.
$out = Join-Path $translations 'ifw_zh_TW.qm'
& $lrelease $catalogs[0] $catalogs[1] -qm $out
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $out) -or (Get-Item -LiteralPath $out).Length -eq 0) {
  throw 'Traditional Chinese compilation failed'
}
Copy-Item -LiteralPath $qtBase -Destination (Join-Path $translations 'qt_zh_TW.qm') -Force
foreach ($name in @('ifw_zh_TW.qm','qt_zh_TW.qm')) {
  $file = $qrc.CreateElement('file')
  $file.InnerText = $name
  [void]$resource.AppendChild($file)
}
# Add the entry last, after all dictionaries are available. This script is an
# opt-in fixture preparation step, not an enablement of the shipped installer.
$item = $ui.CreateElement('item')
$property = $ui.CreateElement('property'); $property.SetAttribute('name','text')
$text = $ui.CreateElement('string'); $text.SetAttribute('notr','true'); $text.InnerText = '繁體中文'
[void]$property.AppendChild($text); [void]$item.AppendChild($property); [void]$combo.AppendChild($item)
$qrc.Save($qrcPath)
$ui.Save((Join-Path $meta 'languagewidget.ui'))
@{
  locale = 'zh_TW'
  qtBaseSource = $qtBase
  qtBaseSHA256 = (Get-FileHash -LiteralPath $qtBase -Algorithm SHA256).Hash
  ifwSHA256 = (Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash
  qtVersion = $qtVersion
  lreleaseVersion = $lreleaseVersion
  note = 'Prepared only; no GUI or restart validation is implied.'
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $translations 'traditional-stage.json') -Encoding UTF8
Write-Host 'Prepared experimental Traditional Chinese resources; rebuild the disposable installer using its translations.qrc.'
