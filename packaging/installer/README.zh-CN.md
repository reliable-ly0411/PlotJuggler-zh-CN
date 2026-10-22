# Windows zh-CN installer: language and identity

Development changes after rc2; this document does not announce a new release.

Output filenames carry `-zh-CN.exe`; development builds also include their source commit.

## Chinese installer and language switching

The installer, component display name, Start Menu group and shortcuts carry
`zh-CN`. The default folder is ASCII-named `PlotJuggler4-zh-CN`; no existing
upstream installation is silently removed or migrated. The canonical IFW
component identifier remains `io.plotjuggler.application` so maintenance data
retains its identity. `-NameSuffix` defaults to `-zh-CN` and can be overridden explicitly.

Packaging requires **Qt Installer Framework 4.10.0 or newer**. The automatic tool helper
pins 4.10.0, whose
`--lang` behavior is used. Standard wizard and Qt dialog translations are
explicitly embedded with `binarycreator -r`, not assumed to exist in IFW's
precompiled runtime. See [catalog provenance and licensing](translations/README.md).
The 700-message standard catalog and the component's custom directory/replacement
catalog are compiled with the selected Qt kit's `lrelease`.

The page immediately after the welcome page exposes 简体中文 / English and a bilingual restart button.
Selection restarts the same executable with `--lang zh_CN` or `--lang en_US`,
before installation or directory selection. A detached Windows PowerShell
process waits for the synchronously verified parent PID to exit before relaunching, avoiding IFW's
single-instance lock. It has a 30-second bound and does not install, purge,
accept licenses or elevate privileges. Repeated clicks are disabled immediately.
The initial language follows the OS locale, as does standard IFW behavior.
A synchronous PowerShell/CIM probe runs before closing the wizard; a failed
probe reports the manual alternative and leaves the wizard open. Newer IFW
versions may add standard strings absent from the pinned 4.10.0 catalog and
require renewed standard-page translation review; they are not silently
claimed to have the candidate toolchain's exact coverage.

On machines whose policy blocks Windows PowerShell or CIM, close the wizard
and run `installer.exe --lang zh_CN` or `installer.exe --lang en_US` manually.
The same options select the maintenance tool's language. No sidecar launcher is
needed. Component pages also implement IFW's `retranslateUi` hook.

Windows validation must cover language-page restart both ways, subsequent standard
and custom pages, Back/Cancel, maintenance mode and a path containing spaces
and an apostrophe. Catalog/unit checks on Linux do not constitute that GUI
acceptance. License agreement originals remain unchanged.

## IFW 工具获取与版本检测

候选固定使用 Qt 官方 IFW 4.10.0 Windows x64 原始工具包：
https://download.qt.io/online/qtsdkrepository/windows_x86/ifw/tools_ifw_410/qt.tools.ifw.410/4.10.0-0-202506090530ifw-win-x64.7z

文件大小 54,561,536 字节，SHA-256：
`bf460f2f60b858d9bfb6c709fc4687fd6967856984bd730711df2c4df9dd49f2`。
`install_ifw.ps1` 必须先校验再解压。官方 `Updates.xml` 的组件名为
`qt.tools.ifw.410`，不是 `.4100`。aqtinstall 3.3.0 的
`list-tool windows desktop tools_ifw` 实测只列出旧目录中的 4.7，故此处不能
直接使用该 aqt 命令获取 4.10。

`binarycreator` 不支持 `--version`。构建器调用其同目录的
`installerbase.exe --version`，检查退出码后读取语义版本。IFW 4.10.0
固定源码 `326d161c66eef5b02a54f01867bc593e0c5f41ac` 的
`src/sdk/main.cpp` 在读取安装元数据前处理该选项，依次输出版本、构建日期、
提交标识并成功退出；这不是安装或发布操作。共用构建器要求至少 4.10，
自动获取的固定工具包则要求 `IFW Version: 4.10.0, built with Qt ...` 前缀。以上不替代 Windows 原生安装界面验收。

构建器未指定 `-IfwDir` 且自动发现工具不存在、版本过旧或不能查询时，会调用
`install_ifw.ps1` 获取以上固定官方工具包。下载、哈希、解压或版本检查任一失败即停止，
不会继续使用旧版。默认放入 `.qt/Tools/QtInstallerFramework/4.10.0-pinned`，
保留包内许可证；已有目标目录不会被覆盖。下载所需 `7z` 不存在也会明确失败。
显式 `-IfwDir` 只从该目录读取工具，不从 PATH 或别处替代，也不自动下载；
离线环境可以提前准备 IFW4.10或更新版本，并传入它的 `bin` 目录。
此流程不修改旧发布工作流，不运行安装器 GUI。标准页真实加载、中英文重启与
安装/维护行为仍需要 Windows 原生验收，参数和静态测试不代表界面通过。

## Windows 资源与语言机制回归测试

启用 `PJ_BUILD_TESTS` 时，`WindowsInstallerResourceContract` 使用已安装 Qt 的
`lrelease` 与现有官方校验下载助手，实际运行 IFW 4.10 `binarycreator`。
真实配置、标准/自定义中文词典与页面只配合明确标记的合成数据，生成临时离线
fixture，断言 PE 及两份内嵌词典和独有资源标记。随后使用 Windows 平台启动此合成
fixture，读取真实欢迎页控件及 QWizard 默认按钮文字，并通过实际语言按钮执行
中文→English→中文重启。测试在目录页修改路径后返回，检查重启保留 `--script`、
`--root` 和所选目录（含空格、中文、单引号），读取中英文自定义目录页文字。
三个进程必须依次自然退出，且始终不进入组件选择或安装阶段，不产生安装目标。
超时只清理唯一临时 fixture 路径对应的进程，不按通用进程名终止其他程序。

此项必须以对应提交的 Windows CTest 结果为准；Linux 的 mock/解析检查不是执行证据。
默认按钮文字来自 IFW 对真实 QWizard 的缓存，不宣称是截图或当前按钮的无障碍读数。
合成机制测试不替代完整应用安装/升级、Explorer/快捷方式和人工视觉验收。
API 依据为 QtIFW 4.10 的
[PackageManagerGui](https://github.com/qtproject/installer-framework/blob/4.10/src/libs/installer/packagemanagergui.cpp)
与 [GuiProxy](https://github.com/qtproject/installer-framework/blob/4.10/src/libs/installer/scriptengine.cpp)。
