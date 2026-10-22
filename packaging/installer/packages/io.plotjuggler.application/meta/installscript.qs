// SPDX-License-Identifier: MPL-2.0
//
// PlotJuggler 4 IFW install script.
//
// Behavior:
// - Per-user install by default (no gainAdminRights). Runs from
//   %LOCALAPPDATA%\PlotJuggler4-zh-CN unless the user picks another dir. Corporate
//   locked-down machines that block UAC prompts still install cleanly.
// - Creates Start Menu + Desktop shortcuts on Windows.
// - Prompts before purging a previous installation in the same directory
//   (the earlier PJ3-inherited flow ran maintenancetool purge silently).

var targetDirectoryPage = null;
var replacementAttempted = false;
// Filled from replacement_guard.ps1 by both real and synthetic builders.
var replacementGuard = "__PJ_REPLACEMENT_HELPER_GZIP__";

function Component()
{
    component.loaded.connect(this, this.installerLoaded);
}

Component.prototype.isDefault = function()
{
    return true;
}

Component.prototype.createOperations = function()
{
    try {
        component.createOperations();
        if (systemInfo.productType === "windows") {
            component.addOperation("CreateShortcut",
                "@TargetDir@/bin/PlotJuggler4.exe",
                "@StartMenuDir@/PlotJuggler 4 zh-CN.lnk",
                "workingDirectory=@TargetDir@/bin", "iconId=0",
                "description=" + qsTranslate("PlotJugglerInstaller", "Launch PlotJuggler 4"));
            component.addOperation("CreateShortcut",
                "@TargetDir@/bin/PlotJuggler4.exe",
                "@DesktopDir@/PlotJuggler 4 zh-CN.lnk",
                "workingDirectory=@TargetDir@/bin", "iconId=0",
                "description=" + qsTranslate("PlotJugglerInstaller", "Launch PlotJuggler 4"));
        }
    } catch (e) {
        console.log(e);
    }
}

// Custom target-directory page — https://stackoverflow.com/a/46614107
Component.prototype.installerLoaded = function()
{
    // Only a fresh GUI install picks a directory or replaces a previous one.
    // The maintenance tool runs this script too, and during an update its
    // TargetDir IS the existing installation: the replace prompt below would
    // purge the very install being updated. A command-line run has no gui.
    if (!installer.isInstaller() || installer.isCommandLineInstance())
        return;

    installer.setDefaultPageVisible(QInstaller.TargetDirectory, false);
    installer.addWizardPage(component, "TargetWidget", QInstaller.TargetDirectory);
    // IFW allocates dynamic pages downwards from the anchor. Register the
    // language page last so it appears before directory selection, after welcome.
    installer.addWizardPage(component, "LanguageWidget", QInstaller.TargetDirectory);
    var languageWidget = component.userInterface("LanguageWidget");
    languageWidget.language.currentIndex = installer.value("UILanguage").indexOf("zh") === 0 ? 0 : 1;
    languageWidget.applyLanguage.clicked.connect(this, this.applyLanguage);

    targetDirectoryPage = gui.pageWidgetByObjectName("DynamicTargetWidget");
    targetDirectoryPage.targetDirectory.textChanged.connect(this, this.targetDirectoryChanged);
    targetDirectoryPage.targetDirectory.setText(installer.value("TargetDir"));
    retranslateTargetDirectory();
    targetDirectoryPage.targetChooser.released.connect(this, this.targetChooserClicked);

    gui.pageById(QInstaller.ComponentSelection).entered.connect(this, this.componentSelectionPageEntered);
}

Component.prototype.targetChooserClicked = function()
{
    var dir = QFileDialog.getExistingDirectory("", targetDirectoryPage.targetDirectory.text);
    targetDirectoryPage.targetDirectory.setText(dir);
}

function updateTargetDirectory()
{
    var dir = targetDirectoryPage.targetDirectory.text;
    if (installer.fileExists(dir) && installer.fileExists(dir + "/maintenancetool.exe")) {
        targetDirectoryPage.warning.setText(qsTranslate("PlotJugglerInstaller", "<p style=\"color: red\">Existing installation detected — it will be replaced on the next page.</p>"));
    }
    else if (installer.fileExists(dir)) {
        targetDirectoryPage.warning.setText(qsTranslate("PlotJugglerInstaller", "<p style=\"color: red\">Installing into an existing directory. Its contents will be wiped on uninstall.</p>"));
    }
    else {
        targetDirectoryPage.warning.setText("");
    }
    installer.setValue("TargetDir", dir);
}

Component.prototype.targetDirectoryChanged = updateTargetDirectory;

Component.prototype.componentSelectionPageEntered = function()
{
    var dir = installer.value("TargetDir");
    if (installer.fileExists(dir) && installer.fileExists(dir + "/maintenancetool.exe")) {
        var answer = QMessageBox["question"]("existing.install",
            qsTranslate("PlotJugglerInstaller", "Replace existing installation?"),
            qsTranslate("PlotJugglerInstaller", "PlotJuggler 4 is already installed at:\n\n") + dir + "\n\n" +
            qsTranslate("PlotJugglerInstaller", "Continuing will uninstall it before the new version is installed. Continue?"),
            QMessageBox.Yes | QMessageBox.No);
        if (answer !== QMessageBox.Yes) {
            gui.rejectPage(QInstaller.ComponentSelection);
            return;
        }
        if (replacementAttempted) {
            gui.rejectWithoutPrompt();
            return;
        }
        replacementAttempted = true;
        var result = [];
        try {
            if (!/^[A-Za-z0-9+/]+=*$/.test(replacementGuard)) throw new Error("guard-not-built");
            var command = "$ErrorActionPreference='Stop'; $bytes=[Convert]::FromBase64String('" + replacementGuard + "'); " +
                "$memory=New-Object IO.MemoryStream(,$bytes); " +
                "$gzip=New-Object IO.Compression.GZipStream($memory,[IO.Compression.CompressionMode]::Decompress); " +
                "$reader=New-Object IO.StreamReader($gzip); " +
                "& ([scriptblock]::Create($reader.ReadToEnd())) -TargetPath '" + String(dir).replace(/'/g, "''") + "'";
            var powershell = installer.environmentVariable("SystemRoot") + "/System32/WindowsPowerShell/v1.0/powershell.exe";
            result = installer.execute(powershell, ["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encodePowerShellCommand(command)]);
        } catch (_) {}
        if (result.length !== 2 || result[1] !== 0 || String(result[0]).trim() !== "PJ_REPLACEMENT_OK" ||
            installer.value("TargetDir") !== dir || installer.fileExists(dir) || installer.fileExists(dir + "/maintenancetool.exe")) {
            var failure = result.length === 2 ? /^PJ_REPLACEMENT_FAILED:(identity|start|wait|residual)\s*$/.exec(String(result[0])) : null;
            console.log("PJ_REPLACEMENT_BLOCKED:" + (failure ? failure[1] : "supervisor-result"));
            QMessageBox.warning("replacement.failed",
                qsTranslate("PlotJugglerInstaller", "Replacement stopped"),
                qsTranslate("PlotJugglerInstaller", "The previous installation could not be safely removed. Setup will close without installing. Its uninstaller may still be running in the background. Do not reinstall into this directory until it has fully finished. Automatic replacement supports verified current-user installations only. For an all-users installation, uninstall it manually and confirm that removal has fully finished."));
            gui.rejectPage(QInstaller.ComponentSelection);
            gui.rejectWithoutPrompt();
            return;
        }
        console.log("PJ_REPLACEMENT_VERIFIED");
    }
}

// Quote one Windows argv entry using CommandLineToArgvW/CRT backslash rules.
function quoteWindowsArgument(argument)
{
    return '"' + String(argument).replace(/(\\*)"/g, function(_, slashes) {
        return slashes + slashes + '\\' + '"';
    }).replace(/(\\+)$/g, function(slashes) { return slashes + slashes; }) + '"';
}

function restartArguments(arguments, language, target)
{
    var result = ["--lang", language];
    var options = true;
    for (var i = 1; i < arguments.length; ++i) {
        var argument = arguments[i];
        if (argument === "--") { options = false; result.push(argument); continue; }
        if (argument.indexOf("TargetDir=") === 0) continue;
        if (!options) { result.push(argument); continue; }
        if (argument === "--lang") { ++i; continue; }
        if (argument.indexOf("--lang=") === 0)
            continue;
        if (argument === "--root" || argument === "-t") {
            result.push(argument, target); ++i; continue;
        }
        if (argument.indexOf("--root=") === 0 || argument.indexOf("-t=") === 0) {
            result.push(argument.substring(0, argument.indexOf("=") + 1) + target); continue;
        }
        result.push(argument);
    }
    result.push("TargetDir=" + target);
    return result;
}

// IFW expands every @name@ pair in execute/executeDetached arguments, even
// inside PowerShell @() / @{} syntax or user argv. UTF-16LE Base64 is the native
// -EncodedCommand protocol and contains no @, so the transport is lossless.
function encodePowerShellCommand(command)
{
    var alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    var bytes = [];
    for (var i = 0; i < command.length; ++i) {
        var code = command.charCodeAt(i);
        bytes.push(code & 255, code >>> 8);
    }
    var encoded = "";
    for (var j = 0; j < bytes.length; j += 3) {
        var value = (bytes[j] << 16) | ((bytes[j + 1] || 0) << 8) | (bytes[j + 2] || 0);
        encoded += alphabet.charAt((value >>> 18) & 63) + alphabet.charAt((value >>> 12) & 63);
        encoded += j + 1 < bytes.length ? alphabet.charAt((value >>> 6) & 63) : "=";
        encoded += j + 2 < bytes.length ? alphabet.charAt(value & 63) : "=";
    }
    return encoded;
}

// IFW's documented <key=value> positional arguments restore TargetDir. Other
// real startup arguments are retained, including proxy/offline options.
Component.prototype.applyLanguage = function()
{
    console.log("PJ_LANGUAGE_RESTART:clicked");
    var widget = component.userInterface("LanguageWidget");
    var language = widget.language.currentIndex === 0 ? "zh_CN" : "en_US";
    if (installer.value("UILanguage") === language)
        return;
    var executable = installer.value("InstallerFilePath").replace(/'/g, "''");
    var target = installer.value("TargetDir");
    var powershell = installer.environmentVariable("SystemRoot") + "/System32/WindowsPowerShell/v1.0/powershell.exe";
    // Read only this synchronous child's actual parent. Never accept argv from
    // a process-name search or caller-provided PID. Access/parse failures keep UI.
    var probeCommand = "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue'; " +
        "$child = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID); " +
        "$parent = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $child.ParentProcessId); " +
        "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class PJInstallerArgv { " +
        "[DllImport(\"shell32.dll\", CharSet=CharSet.Unicode, SetLastError=true)] public static extern IntPtr CommandLineToArgvW(string text, out int count); " +
        "[DllImport(\"kernel32.dll\")] public static extern IntPtr LocalFree(IntPtr memory); " +
        "[DllImport(\"kernel32.dll\", CharSet=CharSet.Unicode, SetLastError=true)] public static extern uint GetLongPathName(string path, System.Text.StringBuilder result, uint size); }'; " +
        "function Resolve-PJLongPath([string]$path) { $buffer=New-Object Text.StringBuilder 32768; " +
        "$length=[PJInstallerArgv]::GetLongPathName([IO.Path]::GetFullPath($path), $buffer, 32768); " +
        "if (!$length -or $length -ge 32768) { throw 'Parent identity mismatch: path resolution failed' }; return $buffer.ToString() }; " +
        "if (!$parent.ExecutablePath -or !$parent.CommandLine -or " +
        "![String]::Equals((Resolve-PJLongPath $parent.ExecutablePath), (Resolve-PJLongPath '" + executable + "'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Parent identity mismatch' }; " +
        "$count = 0; $memory = [PJInstallerArgv]::CommandLineToArgvW($parent.CommandLine, [ref]$count); " +
        "if ($memory -eq [IntPtr]::Zero -or $count -lt 1) { throw 'Invalid parent argv' }; " +
        "try { $argv = @(); for ($i=0; $i -lt $count; $i++) { $argv += [Runtime.InteropServices.Marshal]::PtrToStringUni([Runtime.InteropServices.Marshal]::ReadIntPtr($memory, $i * [IntPtr]::Size)) }; " +
        "$json = @{ pid=$parent.ProcessId; argv=$argv } | ConvertTo-Json -Compress -Depth 4; " +
        "[regex]::Replace($json, '[^\\x00-\\x7F]', { param($m) '\\u{0:x4}' -f [int][char]$m.Value }) " +
        "} finally { [void][PJInstallerArgv]::LocalFree($memory) }";
    var probe = installer.execute(powershell, ["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encodePowerShellCommand(probeCommand)]);
    var parent = null;
    var parsedJson = false;
    try {
        if (probe.length === 2 && probe[1] === 0) {
            parent = JSON.parse(String(probe[0]));
            parsedJson = true;
        }
    } catch (_) {}
    var validPid = parent !== null && /^[1-9][0-9]*$/.test(String(parent.pid));
    var validArray = parent !== null && parent.argv instanceof Array;
    // Fixed metadata only: never log the JSON, raw command line or error text.
    console.log("PJ_LANGUAGE_PROBE:exit=" + (probe.length === 2 ? probe[1] : "missing") +
        ";stdout=" + (probe.length === 2 && String(probe[0]).length > 0) +
        ";json=" + parsedJson + ";pid=" + validPid + ";argv=" + validArray);
    if (!validPid || !validArray || parent.argv.length === 0 || !target) {
        var reason = probe.length !== 2 || probe[1] !== 0 ? "probe-execute" :
            !parsedJson ? "probe-json" : !validPid ? "probe-pid" : !validArray || parent.argv.length === 0 ? "probe-argv" : "probe-target";
        if (String(probe[0]).indexOf("Parent identity mismatch") !== -1) reason = "probe-identity";
        this.languageRestartFailed(reason);
        return;
    }
    for (var i = 0; i < parent.argv.length; ++i) {
        if (typeof parent.argv[i] !== "string") { this.languageRestartFailed("invalid-argv"); return; }
    }
    var arguments = restartArguments(parent.argv, language, target);
    var quoted = [];
    for (var j = 0; j < arguments.length; ++j) quoted.push(quoteWindowsArgument(arguments[j]));
    var command = "$ErrorActionPreference = 'Stop'; " +
        "Wait-Process -Id " + parent.pid + " -Timeout 30 -ErrorAction SilentlyContinue; " +
        "if (Get-Process -Id " + parent.pid + " -ErrorAction SilentlyContinue) { exit 1 }; " +
        "Start-Process -FilePath '" + executable + "' -ArgumentList '" + quoted.join(" ").replace(/'/g, "''") + "'";
    if (installer.executeDetached(powershell, ["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", encodePowerShellCommand(command)])) {
        console.log("PJ_LANGUAGE_RESTART:helper-started");
        widget.applyLanguage.enabled = false;
        gui.rejectWithoutPrompt();
    } else {
        this.languageRestartFailed("helper-start");
    }
}

Component.prototype.languageRestartFailed = function(reason)
{
    console.log("PJ_LANGUAGE_RESTART_FAILED:" + reason);
    QMessageBox.warning("language.restart", qsTranslate("PlotJugglerInstaller", "Language selection"),
        qsTranslate("PlotJugglerInstaller", "Could not restart the installer. Close it and run it with --lang zh_CN or --lang en_US."));
}

// IFW calls this reserved hook through QJSValue::call(), without binding the
// script instance as its receiver. Keep its work independent of `this`.
function retranslateTargetDirectory()
{
    if (targetDirectoryPage === null)
        return;
    targetDirectoryPage.windowTitle = qsTranslate("PlotJugglerInstaller", "Choose Installation Directory");
    targetDirectoryPage.description.setText(qsTranslate("PlotJugglerInstaller", "Please select where PlotJuggler 4 will be installed:"));
    updateTargetDirectory();
}

Component.prototype.retranslateUi = retranslateTargetDirectory;
