# PlotJuggler 4.0.0-zh.1.rc.2 · 简体中文 + ArduPilot BIN（预发布）

这是 4.x 简体中文第二个候选版本，基于官方 `4.0.0` 正式版之后的
`main-4.x` 快照 `0345ec513bde7f05ad3148548ac30401f2b6f7a7`。
它不是未经修改的官方 4.0.0，也不代表上游后续开发快照已正式发布。
本页设置为预发布，不设置为 Latest。保留现有 Latest 状态。

## 上游 4.0.0 发布说明（全文）

来源：[PlotJuggler/PlotJuggler 4.0.0](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.0.0)，
上游发布提交 `d278b1fe98f699d27b820867f454a697e50def2e`。
该 Release 的完整正文如下，没有其他遗漏的条目：

**Full Changelog**: https://github.com/PlotJuggler/PlotJuggler/compare/3.999.9...4.0.0

本候选还包含 [4.0.0 到固定快照的上游提交](https://github.com/PlotJuggler/PlotJuggler/compare/4.0.0...0345ec513bde7f05ad3148548ac30401f2b6f7a7)。
固定快照没有单独的对应上游 Release 正文，不为其编造发布说明。

## 本分支新增内容

本候选在 rc.1 之后补齐启动画面、界面与错误提示；旧标签及原包保持不变。

- 新配置默认简体中文；首选项可切换中文和 English，下次启动生效。命令行 `--language zh_CN` / `--language en_US` 只覆盖本次会话。
- 1,455 条已提取 Qt 消息完成翻译，保留英文源字符串、数据标识与数值解析 locale。这个数字是目录范围内的覆盖率，不代表所有外部插件和脚本文案均已翻译。
- 随包附带可替换的 ArduPilot DataFlash BIN 独立共享插件，固定源提交 `@BIN_SHA@`，版本 `@BIN_VERSION@`；不是静态嵌入应用。
- BIN 支持数值字段、传感器实例、单位、参数和消息时间线，包含中文文件路径、重复加载、多个数据文件隔离和损坏格式回归。
- 固定官方插件 registry 快照 `2696403e106c6960541b8da19987ece35a24597e`；Windows 包含 18 个官方插件和 BIN，Linux 包含 20 个官方插件和 BIN。插件按实际 SDK/ABI 校验。
- 附带 Noto Sans CJK SC 字体及 SIL OFL，避免依赖系统是否已安装中文字体。BIN、字体及应用许可文本保留在包内。

## 下载与安装

- Windows x64：`PlotJuggler-4.0.0-zh.1.rc.2-Windows-x64-zh-CN.exe`。运行离线安装器，选择独立目录；附带 Qt、FFmpeg、Python 和 app-local MSVC 运行库。安装器未签名，未提供远程自动更新仓库。
- Linux x86_64：`PlotJuggler-4.0.0-zh.1.rc.2-x86_64-zh-CN.AppImage`。赋予执行权限后运行；无 FUSE 的环境可设置 `APPIMAGE_EXTRACT_AND_RUN=1`。
- Ubuntu/Debian amd64：`plotjuggler4_4.0.0~zh.1~rc.2-1_amd64-zh-CN.deb`。使用 `sudo apt install ./文件名.deb`，由 apt 安装声明的系统依赖，再运行 `plotjuggler4`。实际干净环境验收覆盖 Ubuntu 22.04 和 24.04；未据此承诺所有 Debian 衍生发行版。
- 下载后按 `SHA256SUMS.txt` 核对 SHA-256。GitHub 自动生成的 Source code 下载只包含主仓库，不包含子模块内容；源码构建请克隆本标签并递归初始化子模块。

应用、tag 和文件名使用同一 SemVer `4.0.0-zh.1.rc.2`（tag 带 `v`）。
Debian 元数据为 `4.0.0~zh.1~rc.2-1`；IFW 数字包版本为 `4.0.0.1.0.2`。
这些是包管理器的有序映射，应用显示的版本没有变成另一个版本。
映射回归保证 rc.1 < rc.2 < 同汉化修订正式版；详见 [发布规范](../../blob/@SOURCE_SHA@/RELEASING.md)。

## 兼容性与已知限制

- 使用 Qt 6.11.1、C++20 和 PlotJuggler SDK 0.34.1。BIN bootstrap ABI 5 / data-source ABI 4；PJ3 Qt5 插件与 PJ4 C ABI 不兼容，不能混用。
- 4.x 是重新设计的应用；不保证完整兼容 3.x 布局文件。建议与 3.x 并行安装，保留原日志及布局备份。
- Linux 主程序及普通插件的 glibc floor 为 2.35。ROS 2 插件的 distro-specific inner 仍需匹配已安装并 source 的 ROS 环境；不将外部 ROS 依赖冒称随包自带。
- Windows 原包在 Windows Server 2022 x64 runner 实际安装、启动、插件加载和卸载。没有把该结果冒称所有 Windows 10/11 配置已实机验证。
- 无 macOS、ARM 或 WebAssembly 发布包。WebAssembly 不启用原生 BIN 共享插件。
- 中文启动横幅、全部 15 条随机字幕、内置 Lua 显示元数据、文件类型、像素查看器和 Qt 文件对话框已补齐；中文模式不会显示烘焙英文趣图。
- 扩展安装/解压、URDF/网格和 GPU 限制提示采用中文模板；动态路径、字段、插件 ID、第三方库错误及外部插件自带内容保留原文。不能将应用目录覆盖率解释为任意外部插件均已汉化。
- Windows 安装器自定义目录及覆盖确认页提供简体中文目录，标准页跟随 IFW/系统语言；许可证原文不改写。
- SDK 未提供旧版逐字段 tooltip setter，字段说明保留在数据集元数据；具体差异见 [BIN SDK4 说明](https://github.com/reliable-ly0411/plotjuggler-apbin-plugins/blob/@BIN_SHA@/sdk4/UPSTREAM.md)。
- 上游更新提示/apt 指引仍指向上游官方渠道；本候选没有汉化自动更新服务。升级汉化版请从本仓库 Release 手动下载，勿把上游更新提示当作汉化更新。
- 3.x 历史启动图像问题 [#3](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/3) 未因此声明解决。4.x 包验收不替代该独立问题的验证。

## 验收和来源

源码提交：`@SOURCE_SHA@`；源码树：`@SOURCE_TREE@`。
候选构建与原包验收：[GitHub Actions @RUN_ID@](@RUN_URL@)。

- 两平台原生回归包括翻译检查、语言首选项、真实主窗口和 BIN 解析/动态加载/主应用导入测试。通过、跳过及未运行项以该固定运行的报告为准，不把跳过视为通过。
- 最终 Windows IFW 原包实际安装后校验内嵌版本、19 个插件、Python 后端、中文路径真实 BIN 的 1,940 条数值序列及曲线绑定，然后卸载。
- 最终 AppImage 和 .deb 原包在无 Qt/Conan 构建树的 Ubuntu 22.04 / 24.04 环境验收，检查版本及 21 个插件的包内清单，实际加载其中 20 个；ROS 2 插件保留在包内，但干净环境未安装 ROS，其运行功能未验收。另检查 Python、中文路径真实 BIN 及中英文界面截图；不使用临时重新打包的产物代替。
- 真实测试 BIN 自身具有截断尾记录警告，保留该事实；无未绑定曲线或错误级诊断。测试报告和截图留在 CI 工件中，不混入下载附件。
- 发布只提升已验收的同一批包，公开后重新下载核对大小和 SHA-256，不重新构建、不覆盖旧附件。

应用为 MPL-2.0；独立 BIN 插件为 LGPLv3，SDK 保持其原有 Apache-2.0 许可；
Qt、官方插件和字体按各自许可分发。对应源代码和许可链接见包内 `share/licenses` 与源码子模块。

## 原包校验

@ASSET_TABLE@
