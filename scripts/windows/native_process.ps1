# SPDX-License-Identifier: MPL-2.0
# Explicitly wait for GUI-subsystem executables in PowerShell 5.1 and 7.
function ConvertTo-PjNativeArgument([AllowEmptyString()][string]$Value) {
  # Windows CRT/CommandLineToArgvW quoting, including empty args, embedded
  # quotes and trailing backslashes. ProcessStartInfo.ArgumentList is not
  # available on Windows PowerShell's .NET Framework.
  $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
  $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
  return '"' + $escaped + '"'
}

function Invoke-PjNativeProcess([string]$FilePath, [string[]]$ArgumentValues = @(), [switch]$InheritOutput) {
  $info = New-Object Diagnostics.ProcessStartInfo
  $info.FileName = $FilePath
  $info.Arguments = (@($ArgumentValues | ForEach-Object { ConvertTo-PjNativeArgument $_ }) -join ' ')
  $info.UseShellExecute = $false
  $info.RedirectStandardOutput = !$InheritOutput
  $info.RedirectStandardError = !$InheritOutput
  if (!$InheritOutput) {
    $info.StandardOutputEncoding = New-Object Text.UTF8Encoding($false)
    $info.StandardErrorEncoding = New-Object Text.UTF8Encoding($false)
  }
  $process = New-Object Diagnostics.Process
  $process.StartInfo = $info
  try {
    if (!$process.Start()) { throw 'Application process did not start' }
    if ($InheritOutput) {
      # Long-running developer GUI: inherit the parent's handles so diagnostics
      # remain live, without retaining its whole session in memory.
      $process.WaitForExit()
      return [pscustomobject]@{ ExitCode = $process.ExitCode; StandardOutput = $null; StandardError = $null }
    }
    # Drain BOTH streams concurrently: reading either synchronously can deadlock
    # when the other fills its pipe. WaitForExit, never a stale LASTEXITCODE.
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    return [pscustomobject]@{
      ExitCode = $process.ExitCode
      StandardOutput = $stdout.GetAwaiter().GetResult()
      StandardError = $stderr.GetAwaiter().GetResult()
    }
  } finally { $process.Dispose() }
}
