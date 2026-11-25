# PlotJuggler 4.0.0-zh.1.rc.3 · 简体中文 + ArduPilot BIN（预发布）

这是 4.x 简体中文第三个候选版本，纳入稳定维护线 `zh-CN-4.x`。
基线仍是官方 `4.0.0` 正式版之后的 `main-4.x` 快照
`0345ec513bde7f05ad3148548ac30401f2b6f7a7`。
它不是未经修改的官方 4.0.0，也不代表上游后续开发快照已正式发布。
本页设置为预发布，不设置为 Latest。旧标签及原包保持不变。

## 上游 4.0.0 发布说明（全文）

来源：[PlotJuggler/PlotJuggler 4.0.0](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.0.0)，
上游发布提交 `d278b1fe98f699d27b820867f454a697e50def2e`。
该 Release 的完整正文如下，没有其他遗漏的条目：

**Full Changelog**: https://github.com/PlotJuggler/PlotJuggler/compare/3.999.9...4.0.0

本候选还包含 [4.0.0 到固定快照的上游提交](https://github.com/PlotJuggler/PlotJuggler/compare/4.0.0...0345ec513bde7f05ad3148548ac30401f2b6f7a7)。
固定快照没有单独的对应上游 Release 正文，不为其编造发布说明。

## 本分支新增内容

本候选在 rc.2 之后补齐 Windows 集成、安装器语言切换、插件迁移及界面翻译。

- 新配置默认简体中文；首选项可切换中文和 English，下次启动生效。命令行 `--language zh_CN` / `--language en_US` 只覆盖本次会话。首选项按两种语言的布局尺寸保持控件可达。
- 1,968 条已提取 Qt 消息完成翻译，保留英文源字符串、数据标识与数值解析 locale。这是指定目录的覆盖率，不代表所有外部插件和脚本文案均已翻译。
- Windows 主程序使用 GUI 子系统和内嵌多尺寸图标，保留继承或重定向的 CLI 输出。原生测试检查实际 PE 的子系统、图标和诊断输出。
- Windows 安装器、组件、快捷方式和开始菜单使用 `zh-CN` 品牌，默认目录为 ASCII 名称 `PlotJuggler4-zh-CN`。IFW 4.10.0 显式嵌入标准页和 Qt 对话框中文；欢迎页后可选择简体中文/English，重启同一安装器并保留参数和目标目录。目录替换通过真实维护工具及注册信息核验，不静默清除上游安装。
- 更新检查查询本仓同一主版本的汉化发布列表，比较汉化修订和候选序号，提供手动下载。AppImage 外部链接恢复宿主环境，避免捆绑 Qt/动态库影响系统浏览器。
- 固定市场目录 30 项（Windows 可用 29 项）的名称、描述和分类采用显示翻译，保留英文搜索、canonical ID、URL 和协议。默认随包数量见下文。
- 同版本汉化插件在扫描前按精确旧构建来源和真实 DSO SHA-256 安全迁移；保留未知用户替换、后续市场更新及成功 receipt。Windows 插件路径和来源记录保留原生 Unicode。
- 中文趣图池包含原 37 张中可用的 33 张（31 张中文像素版本、2 张仅含产品/技术名原图）及额外 8 组 Qt 可翻译双格趣图，共 41 项。原编号 09/11/13/24 未完成，排除于中文池且不回退英文图；英文原池不变。中文会话尊重趣图/严肃启动图设置。15 条随机字幕、内置 Lua 显示元数据和文件对话框继续翻译。
- 可显式使用 `--profile-dir` 隔离应用设置、市场仓库、缓存和临时目录；这不是插件沙箱，也不约束 IFW 安装器。详见 [独立测试配置](../../blob/@SOURCE_SHA@/docs/localization/ISOLATED_PROFILE.zh-CN.md)。
- 随包附带可替换的 ArduPilot DataFlash BIN 独立共享插件，固定源提交 `@BIN_SHA@`，版本 `@BIN_VERSION@`；不是静态嵌入应用。本次不另行发布独立插件版本。
- BIN 支持数值字段、传感器实例、单位、参数和消息时间线，覆盖中文文件路径、重复加载、多个数据文件隔离和损坏格式回归。
- 固定官方插件 registry 快照 `2696403e106c6960541b8da19987ece35a24597e`；Windows 包含 18 个官方插件和 BIN，Linux 包含 20 个官方插件和 BIN。插件按实际 SDK/ABI 校验。
- 固定随包官方插件的标题、控件及动态说明采用限定版本/控件的显示映射；不改数据列、路径、代码、协议值或事件标识。
- MCAP、Protobuf、Transform Editor、WebRTC，以及 Linux 的 Assistant 由固定上游源码加本仓显示补丁重建。它们不是上游原始二进制，不冒用上游签名；保留兼容 ID/版本，新二进制哈希、源码/tag/SDK、补丁及依赖来源见包内 release.json 和许可证目录。插件市场更新可能覆盖这些汉化重建版本。
- 本版汉化重建集合共 5 个，Windows 使用其中 4 个，Linux 使用全部 5 个：`mcap-loader`、`protobuf-parser`、`toolbox-transform-editor`、`webrtc-client`、`toolbox-assistant-agent`（仅 Linux）。Mosaico 不属于重建集合。
- 附带 Noto Sans CJK SC 字体及 SIL OFL，避免依赖系统是否已安装中文字体。BIN、字体及应用许可文本保留在包内。

## 下载与安装

- Windows x64：`PlotJuggler-4.0.0-zh.1.rc.3-Windows-x64-zh-CN.exe`。运行离线安装器，选择独立目录；附带 Qt、FFmpeg、Python 和 app-local MSVC 运行库。安装器未签名，未提供远程自动更新仓库。
- Linux x86_64：`PlotJuggler-4.0.0-zh.1.rc.3-x86_64-zh-CN.AppImage`。赋予执行权限后运行；无 FUSE 的环境可设置 `APPIMAGE_EXTRACT_AND_RUN=1`。
- Ubuntu/Debian amd64：`plotjuggler4_4.0.0~zh.1~rc.3-1_amd64-zh-CN.deb`。使用 `sudo apt install ./文件名.deb`，由 apt 安装声明的系统依赖，再运行 `plotjuggler4`。实际干净环境验收覆盖 Ubuntu 22.04 和 24.04；未据此承诺所有 Debian 衍生发行版。
- 下载后按 `SHA256SUMS.txt` 核对 SHA-256。GitHub 自动生成的 Source code 下载只包含主仓库，不包含子模块内容；源码构建请克隆本标签并递归初始化子模块。

应用、tag 和文件名使用同一 SemVer `4.0.0-zh.1.rc.3`（tag 带 `v`）。
Debian 元数据为 `4.0.0~zh.1~rc.3-1`；IFW 数字包版本为 `4.0.0.1.0.3`。
公开下载名仅将 Debian 文件名中的 `~` 映射为 `.`，包内版本和原包字节不变。
这些是包管理器的有序映射，应用显示的版本没有变成另一个版本。
映射保持 rc.1 < rc.2 < rc.3 < 同汉化修订正式版；详见 [发布规范](../../blob/@SOURCE_SHA@/RELEASING.md)。

## 兼容性与已知限制

- Mosaico 1.3.0 明确保留官方原始二进制及剩余英文，未从包中移除。已安全限定的静态控件翻译保留，但 Info、元数据混合正文及部分状态不做猜测替换，以保护原始用户/服务器数据。独立 SDK 重建再分发许可依据尚未核实，并非认定禁止。后续跟踪 [#20](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/20)；本版不宣称所有插件绝对全中文。
- 主程序使用 Qt 6.11.1、C++20 和 PlotJuggler SDK 0.34.1。汉化重建插件分别使用其上游固定的 SDK 0.20.0、0.32.0 或 0.34.1，不相互替换。BIN bootstrap ABI 5 / data-source ABI 4；PJ3 Qt5 插件与 PJ4 C ABI 不兼容，不能混用。
- 4.x 是重新设计的应用；不保证完整兼容 3.x 布局文件。建议与 3.x 并行安装，保留原日志及布局备份。
- Linux 主程序及普通插件的 glibc floor 为 2.35。ROS 2 插件的 distro-specific inner 仍需匹配已安装并 source 的 ROS 环境；不将外部 ROS 依赖冒称随包自带。
- Windows 原包在 Windows Server 2022 x64 runner 实际安装、启动、插件加载和卸载。Windows 未进行人工可见桌面目视验收；原生 PE、合成 IFW 控件/语言重启机制、自动安装及截图证据不等于 Explorer、快捷方式或全部安装页的人工桌面操作，也不代表所有 Windows 10/11 配置已实机验证。
- 无 macOS、ARM 或 WebAssembly 发布包。WebAssembly 不启用原生 BIN 共享插件。
- 扩展安装/解压、URDF/网格和 GPU 限制提示采用中文模板；动态路径、字段、插件 ID、第三方库错误及用户/模型生成内容保留原文。不能将应用目录覆盖率解释为任意外部插件均已汉化。
- 安装器语言切换依赖 Windows PowerShell/CIM；受系统策略限制时，可关闭后手动以 `--lang zh_CN` 或 `--lang en_US` 启动。首次语言跟随系统；许可证原文不改写。
- SDK 未提供旧版逐字段 tooltip setter，字段说明保留在数据集元数据；具体差异见 [BIN SDK4 说明](https://github.com/reliable-ly0411/plotjuggler-apbin-plugins/blob/@BIN_SHA@/sdk4/UPSTREAM.md)。
- 本版没有汉化 IFW/APT 自动更新服务。升级汉化版请从本仓库 Release 手动下载。
- 3.x 历史启动图像问题 [#3](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/3) 及 Qt5 PR #6 不在本版验收范围，未因此声明解决。

## 验收和来源

源码提交：`@SOURCE_SHA@`；源码树：`@SOURCE_TREE@`。
候选构建与最终原包验收：[GitHub Actions @RUN_ID@](@RUN_URL@)。
发布提升的是该精确提交、该 run/attempt 的原始产物；稳定维护线通过普通 merge 保留开发历史。

- 两平台原生回归包括翻译检查、语言首选项、真实主窗口、独立 profile、安装器机制和 BIN 解析/动态加载/主应用导入测试。通过、失败、跳过及未运行项以该固定运行的报告为准，不把跳过视为通过。
- 最终 Windows IFW 原包实际安装后校验内嵌版本、19 个插件、Python 后端、中文路径真实 BIN 的 1,940 条数值序列及曲线绑定，然后卸载。
- 最终 AppImage 和 .deb 原包在无 Qt/Conan 构建树的 Ubuntu 22.04 / 24.04 环境验收，检查版本及 21 个插件的包内清单，实际加载其中 20 个；ROS 2 插件保留在包内，但干净环境未安装 ROS，其运行功能未验收。另检查 Python、中文路径真实 BIN 及中英文界面截图；不使用临时重新打包的产物代替。
- 真实测试 BIN 自身具有截断尾记录警告，保留该事实；无未绑定曲线或错误级诊断。测试还检查实际绘图适配器中的可见有限采样、物理范围和非默认视口，避免仅以导入消息或目录绑定作为曲线证据。测试报告和截图留在 CI 工件中，不混入下载附件。
- 发布只提升已验收的同一批包，公开前后重新下载核对名称、大小和 SHA-256，不重新构建、不覆盖旧附件。最终中英文包截图另外检查，不能据此扩大为未执行的平台或人工桌面验收。

应用为 MPL-2.0；独立 BIN 插件为 LGPLv3，SDK 保持其原有 Apache-2.0 许可；
Qt、官方插件和字体按各自许可分发。对应源代码和许可链接见包内 `share/licenses` 与源码子模块。

## 原包校验

@ASSET_TABLE@
