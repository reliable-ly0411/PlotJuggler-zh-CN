/****************************************************************************
**
** Copyright (C) 2017 The Qt Company Ltd.
** Contact: https://www.qt.io/licensing/
**
** This file is part of the FOO module of the Qt Toolkit.
**
** $QT_BEGIN_LICENSE:GPL-EXCEPT$
** Commercial License Usage
** Licensees holding valid commercial Qt licenses may use this file in
** accordance with the commercial license agreement provided with the
** Software or, alternatively, in accordance with the terms contained in
** a written agreement between you and The Qt Company. For licensing terms
** and conditions see https://www.qt.io/terms-conditions. For further
** information use the contact form at https://www.qt.io/contact-us.
**
** GNU General Public License Usage
** Alternatively, this file may be used under the terms of the GNU
** General Public License version 3 as published by the Free Software
** Foundation with exceptions as appearing in the file LICENSE.GPL3-EXCEPT
** included in the packaging of this file. Please review the following
** information to ensure the GNU General Public License requirements will
** be met: https://www.gnu.org/licenses/gpl-3.0.html.
**
** $QT_END_LICENSE$
**
****************************************************************************/

// Keep Qt IFW's standard target-directory validation. Never execute a foreign
// maintenance tool, purge an existing directory, or uninstall merely by moving
// to the component-selection page. Upgrade by explicitly uninstalling the old
// 3.x package first; user configuration lives outside the installation directory.
function Component()
{
}

Component.prototype.isDefault = function()
{
    return true;
}

Component.prototype.createOperations = function()
{
    component.createOperations();
    if (systemInfo.productType === "windows") {
        component.addOperation("CreateShortcut", "@TargetDir@/plotjuggler-launcher.exe",
            "@StartMenuDir@/PlotJuggler 3 中文版.lnk", "workingDirectory=@TargetDir@",
            "iconId=0", "description=Launch PlotJuggler 3");
        component.addOperation("CreateShortcut", "@TargetDir@/plotjuggler-launcher.exe",
            "@DesktopDir@/PlotJuggler 3 中文版.lnk", "workingDirectory=@TargetDir@",
            "iconId=0", "description=Launch PlotJuggler 3");
    }
}
