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
    this.retranslateUi();
    targetDirectoryPage.targetChooser.released.connect(this, this.targetChooserClicked);

    gui.pageById(QInstaller.ComponentSelection).entered.connect(this, this.componentSelectionPageEntered);
}

Component.prototype.targetChooserClicked = function()
{
    var dir = QFileDialog.getExistingDirectory("", targetDirectoryPage.targetDirectory.text);
    targetDirectoryPage.targetDirectory.setText(dir);
}

Component.prototype.targetDirectoryChanged = function()
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

// IFW loads standard and component translators at process startup. Restart only
// from the language page, before a directory or installation is selected.
Component.prototype.applyLanguage = function()
{
    var widget = component.userInterface("LanguageWidget");
    var language = widget.language.currentIndex === 0 ? "zh_CN" : "en_US";
    if (installer.value("UILanguage") === language)
        return;
    var executable = installer.value("InstallerFilePath").replace(/'/g, "''");
    var powershell = installer.environmentVariable("SystemRoot") + "/System32/WindowsPowerShell/v1.0/powershell.exe";
    // Verify PowerShell/CIM access before closing this wizard. The synchronous
    // child reports this installer's PID; restricted machines keep their UI.
    var probe = installer.execute(powershell, ["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command",
        "$ErrorActionPreference = 'Stop'; (Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID)).ParentProcessId"]);
    var parentId = probe.length === 2 ? String(probe[0]).replace(/\s/g, "") : "";
    if (probe.length !== 2 || probe[1] !== 0 || !/^[1-9][0-9]*$/.test(parentId)) {
        this.languageRestartFailed();
        return;
    }
    // Wait for the verified old PID rather than a fixed sleep. Literal strings
    // keep the installer filename outside PowerShell's command grammar.
    var command = "$ErrorActionPreference = 'Stop'; " +
        "Wait-Process -Id " + parentId + " -Timeout 30 -ErrorAction SilentlyContinue; " +
        "if (Get-Process -Id " + parentId + " -ErrorAction SilentlyContinue) { exit 1 }; " +
        "Start-Process -FilePath '" + executable + "' -ArgumentList '--lang', '" + language + "'";
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

Component.prototype.retranslateUi = function()
{
    if (targetDirectoryPage === null)
        return;
    targetDirectoryPage.windowTitle = qsTranslate("PlotJugglerInstaller", "Choose Installation Directory");
    targetDirectoryPage.description.setText(qsTranslate("PlotJugglerInstaller", "Please select where PlotJuggler 4 will be installed:"));
    this.targetDirectoryChanged();
}
