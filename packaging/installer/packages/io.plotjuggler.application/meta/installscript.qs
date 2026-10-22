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
        installer.execute(dir + "/maintenancetool.exe", ["purge", "-c"]);
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

// IFW's documented <key=value> positional arguments restore TargetDir. Other
// real startup arguments are retained, including proxy/offline options.
Component.prototype.applyLanguage = function()
{
    var widget = component.userInterface("LanguageWidget");
    var language = widget.language.currentIndex === 0 ? "zh_CN" : "en_US";
    if (installer.value("UILanguage") === language)
        return;
    var executable = installer.value("InstallerFilePath").replace(/'/g, "''");
    var target = installer.value("TargetDir");
    var powershell = installer.environmentVariable("SystemRoot") + "/System32/WindowsPowerShell/v1.0/powershell.exe";
    // Read only this synchronous child's actual parent. Never accept argv from
    // a process-name search or caller-provided PID. Access/parse failures keep UI.
    var probeCommand = "$ErrorActionPreference = 'Stop'; " +
        "$child = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID); " +
        "$parent = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $child.ParentProcessId); " +
        "if (!$parent.ExecutablePath -or !$parent.CommandLine -or " +
        "![String]::Equals([IO.Path]::GetFullPath($parent.ExecutablePath), [IO.Path]::GetFullPath('" + executable + "'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Parent identity mismatch' }; " +
        "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class PJInstallerArgv { " +
        "[DllImport(\"shell32.dll\", CharSet=CharSet.Unicode, SetLastError=true)] public static extern IntPtr CommandLineToArgvW(string text, out int count); " +
        "[DllImport(\"kernel32.dll\")] public static extern IntPtr LocalFree(IntPtr memory); }'; " +
        "$count = 0; $memory = [PJInstallerArgv]::CommandLineToArgvW($parent.CommandLine, [ref]$count); " +
        "if ($memory -eq [IntPtr]::Zero -or $count -lt 1) { throw 'Invalid parent argv' }; " +
        "try { $argv = @(); for ($i=0; $i -lt $count; $i++) { $argv += [Runtime.InteropServices.Marshal]::PtrToStringUni([Runtime.InteropServices.Marshal]::ReadIntPtr($memory, $i * [IntPtr]::Size)) }; " +
        "$json = @{ pid=$parent.ProcessId; argv=$argv } | ConvertTo-Json -Compress -Depth 4; " +
        "[regex]::Replace($json, '[^\\x00-\\x7F]', { param($m) '\\u{0:x4}' -f [int][char]$m.Value }) " +
        "} finally { [void][PJInstallerArgv]::LocalFree($memory) }";
    var probe = installer.execute(powershell, ["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", probeCommand]);
    var parent = null;
    try { if (probe.length === 2 && probe[1] === 0) parent = JSON.parse(String(probe[0])); } catch (_) {}
    if (!parent || !/^[1-9][0-9]*$/.test(String(parent.pid)) ||
        !(parent.argv instanceof Array) || parent.argv.length === 0 || !target) {
        this.languageRestartFailed();
        return;
    }
    for (var i = 0; i < parent.argv.length; ++i) {
        if (typeof parent.argv[i] !== "string") { this.languageRestartFailed(); return; }
    }
    var arguments = restartArguments(parent.argv, language, target);
    var quoted = [];
    for (var j = 0; j < arguments.length; ++j) quoted.push(quoteWindowsArgument(arguments[j]));
    var command = "$ErrorActionPreference = 'Stop'; " +
        "Wait-Process -Id " + parent.pid + " -Timeout 30 -ErrorAction SilentlyContinue; " +
        "if (Get-Process -Id " + parent.pid + " -ErrorAction SilentlyContinue) { exit 1 }; " +
        "Start-Process -FilePath '" + executable + "' -ArgumentList '" + quoted.join(" ").replace(/'/g, "''") + "'";
    if (installer.executeDetached(powershell, ["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", command])) {
        widget.applyLanguage.enabled = false;
        gui.rejectWithoutPrompt();
    } else {
        this.languageRestartFailed();
    }
}

Component.prototype.languageRestartFailed = function()
{
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
