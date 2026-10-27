# PlotJuggler 4.0.0-zh.1.rc.4 · 简体中文 + ArduPilot BIN（开发预发布）

这是从 `zh-CN-4.x-dev` 开发集成线准备的第四个 4.x 简体中文候选版本。
主要目的是修复 Windows 下 CSV 文件位于非 ASCII 目录或使用非 ASCII 文件名时，
预览为空、实际导入失败的问题，并把修复接入可追溯的原生插件构建和最终包验收。
本页设置为预发布，不设置为 Latest；旧标签及原包保持不变。
本候选不是稳定正式版，也不是未经修改的官方 4.0.0。

本次开发基线为 `8d0b30ee387946c2881a371edcec8e6b3878df1a`。
相对已发布的 rc.3 标签 `057f707e017c4e296da93efc1272e932eb672738`，
功能变化仅为 CSV 原子修复及其测试、构建、来源与包验收集成；
其余变化是本候选版本标识和发布文档。没有新增上游宿主快照或 SDK 升级。
完整差异见 [rc.3 到本候选源码](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/compare/v4.0.0-zh.1.rc.3...@SOURCE_SHA@)。

## 上游 4.0.0 发布说明（全文）

来源：[PlotJuggler/PlotJuggler 4.0.0](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.0.0)，
上游发布提交 `d278b1fe98f699d27b820867f454a697e50def2e`。
该 Release 的完整正文如下，没有其他遗漏的条目：

**Full Changelog**: https://github.com/PlotJuggler/PlotJuggler/compare/3.999.9...4.0.0

宿主仍固定在该正式版之后的 `main-4.x` 快照
`0345ec513bde7f05ad3148548ac30401f2b6f7a7`。
[4.0.0 到该快照的提交](https://github.com/PlotJuggler/PlotJuggler/compare/4.0.0...0345ec513bde7f05ad3148548ac30401f2b6f7a7)
属于此前候选已经继承的上游范围；rc.4 不额外纳入更晚的上游开发提交。
固定快照没有独立对应的上游 Release 正文，不为其编造发布说明。

## 本版新增：CSV 非 ASCII 路径修复

- 官方 CSV Loader 1.0.7 的预览和导入分别通过两个文件打开点读取输入。
  宿主传递 UTF-8 路径；Windows 窄字符文件流可能按系统代码页解释这些字节，
  因而文件本身有效、同一文件放在 ASCII 路径可打开，换成中文路径却无法打开。
  这不是针对 CSV 字段名、长整数或行数的解析规则修改。
- `CsvDialog::analyzeFile` 与 `CsvSource::importData` 均将 UTF-8 字节保存在拥有自身内存的
  `std::u8string` 中，再经 `std::filesystem::path` 交给原生文件流。
  同时修复预览和实际导入，不改变 CSV 内容解码、数值、时间戳、数值 locale、
  已保存路径字符串、插件 ID/版本或宿主/SDK ABI。
- 动态插件回归使用完全合成 CSV，通过真实插件 ABI 覆盖预览、导入、ASCII、
  中文及补充平面 Unicode 路径、缺失文件等行为，并逐个比较合成数值与时间戳。
  既有解析测试保留；合成输入无需任何私人飞控日志。
- 打包不只是携带一个未被使用的 patch：锁文件固定上游源提交、tag、SDK 和补丁哈希，
  实际构建器应用修复、编译插件和回归测试，再记录许可证、分发身份及新 DSO 哈希。
  最终包验收再次核对实际载入文件及来源。
- 同版本迁移只接纳已核验的官方 Linux/Windows CSV 1.0.7 前驱 DSO；
  未知用户替换文件不会因此被放入可信迁移集合。官方 ZIP 校验和仍只代表官方原包，
  不用于冒充本候选重建的二进制。

实现提交：`cec9b81909706059fd81a8897d284850ffa86c33`，通过
[开发 PR27](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/pull/27) 和
[稳定维护 PR28](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/pull/28)
保留同一原子修复及普通 merge 历史。
核心补丁 SHA-256：
`00ecc1514fde0b6d8b97750a1cac1d2a251c0aa955c884e1dde7fa995f95c02c`。

[上游 PR337](https://github.com/PlotJuggler/pj-official-plugins/pull/337)
在本次说明准备时仍为 draft、未合并，CI 需上游维护者批准。
上游当前目标使用 SDK `0.38.0-dev.3`；本候选固定 SDK `0.34.1` 的构建通过
不等于已验证该更新 SDK。发布前再次核对 PR 状态，不代替上游作合并决定。

## 延续的汉化、插件和 BIN 功能

以下是 rc.3 已有功能，rc.4 保留其实现，不将它们重复描述为本次新增修复：

- 新配置默认简体中文，首选项可切换 English，下次启动生效；
  `--language zh_CN` / `--language en_US` 只覆盖本次会话。
  1,968 条已提取 Qt 消息完成翻译，保留英文源字符串和数据标识；
  该目录覆盖率不代表任意第三方插件均已汉化。
- Windows GUI 子系统、嵌入图标、可重定向 CLI、zh-CN 安装器品牌、
  IFW 标准页译文和安装器语言切换保持原有实现。更新检查提供本仓同主版本的手动下载入口。
- 固定市场目录 30 项（Windows 可用 29 项）的名称、描述和分类采用限定显示映射，
  保留 canonical ID、英文搜索、URL、协议及用户数据。
- 中文趣图池保持 41 项：原 37 张中可用的 33 张加 8 组 Qt 可翻译双格趣图。
  原编号 09/11/13/24 未完成，未进入中文池；英文原池不变。
  15 条随机字幕、内置 Lua 显示元数据与文件对话框沿用现有译文。
- `--profile-dir` 可隔离应用设置、市场仓库、缓存及临时目录。
  它不是插件沙箱，也不约束 IFW 安装器；参见
  [独立配置说明](../../blob/@SOURCE_SHA@/docs/localization/ISOLATED_PROFILE.zh-CN.md)。
- ArduPilot DataFlash BIN 继续作为可替换的独立共享插件随包分发：
  版本 `@BIN_VERSION@`，源提交 `@BIN_SHA@`。
  保留数值字段、实例、单位、参数和消息时间线，以及中文路径、重复导入、多文件隔离、
  损坏格式和曲线恢复回归；没有将 LGPL 解析器静态嵌入应用。
- 固定官方 registry 快照仍为 `2696403e106c6960541b8da19987ece35a24597e`。
  Windows 包含 18 个官方插件和 BIN；Linux 包含 20 个官方插件和 BIN。
  CSV 继续使用兼容 ID/版本 1.0.7，以来源记录和新产物哈希区分本地修复构建。
- 本版汉化重建集合共 6 个，Windows 使用其中 5 个，Linux 使用全部 6 个：`mcap-loader`、`protobuf-parser`、`toolbox-transform-editor`、`webrtc-client`、`toolbox-assistant-agent`、`csv-loader`。
  其中 Assistant 仅在 Linux 提供；CSV 是路径功能修复，其他五项延续既有显示补丁。
  Mosaico 不属于重建集合。每个重建件均保留自己的源/tag/SDK、补丁和许可证身份。
- Noto Sans CJK SC 字体与 SIL OFL、应用和插件许可继续随包提供。

**明确未纳入本版：** APBIN 已安装插件详情中的作者/许可证/访问网站入口补全，
以及 FFT 工具菜单、动态面板和提示的完整汉化修复。
这两项尚未合入本发布源码，不因 BIN 继续随包或 CSV 修复通过而声称已经解决。
本版不另行发布新的 APBIN 或 FFT 插件版本。

## 下载、安装、升级与回退

- Windows x64：`PlotJuggler-4.0.0-zh.1.rc.4-Windows-x64-zh-CN.exe`。
  使用离线安装器；建议开发候选采用独立目录。
  随包包含 Qt、FFmpeg、Python 和 app-local MSVC 运行库。
  安装器未签名；没有汉化 IFW 自动更新服务或远程更新仓库。
- Linux x86_64：`PlotJuggler-4.0.0-zh.1.rc.4-x86_64-zh-CN.AppImage`。
  赋予执行权限后运行；没有 FUSE 时可设置 `APPIMAGE_EXTRACT_AND_RUN=1`。
- Ubuntu/Debian amd64：`plotjuggler4_4.0.0~zh.1~rc.4-1_amd64-zh-CN.deb`。
  用 `sudo apt install ./文件名.deb` 安装，由 apt 处理声明的运行依赖，
  再运行 `plotjuggler4`。实际验收目标为 Ubuntu 22.04 与 24.04；
  不据此承诺所有 Debian 衍生发行版。
- 下载后核对同页 `SHA256SUMS.txt`。GitHub 自动生成的 Source code ZIP/TAR
  不包含子模块内容；源码构建应检出本标签并递归初始化固定子模块。

升级前保存布局与配置备份；开发版建议用新的 `--profile-dir` 目录验证。
已有未知第三方插件或后续市场版本会按原有来源策略保留，不保证自动被修复版本替换。
需要确认 CSV 修复已生效时，应核对实际加载插件的版本、来源记录和 DSO 哈希，
或使用干净独立 profile 验证，不能只看市场里相同的 1.0.7 字样。
市场升级可能重新安装官方 CSV/其他插件并覆盖本候选的重建修复或汉化版本。

回退时正常退出应用：AppImage 可重新运行保留的 rc.3 文件；
Windows 可用本候选维护工具正常卸载，再安装保留的旧版到独立目录；
DEB 可由 apt 显式安装保留的旧版包，若提示降级，确认目标版本后处理。
恢复升级前配置备份，保留当前配置供排查，不假设新旧布局格式完全兼容。
rc.3 本身不含本次 CSV 修复，回退后该问题可能重新出现。
没有本汉化分支的 APT 自动更新发布；不要把其他上游更新源当成本候选更新渠道。

版本映射：应用和下载名 `4.0.0-zh.1.rc.4`，tag `v4.0.0-zh.1.rc.4`，
Debian 包内版本 `4.0.0~zh.1~rc.4-1`，IFW 数字包版本 `4.0.0.1.0.4`。
公开 DEB 文件名仅将 `~` 映射为 `.`；不修改包内版本或原包字节。
排序保持 rc.3 < rc.4 < 同汉化修订正式版。

## 本次构建、验收与溯源

源码提交：`@SOURCE_SHA@`；源码树：`@SOURCE_TREE@`。
候选构建和最终原包验收：[GitHub Actions @RUN_ID@](@RUN_URL@)。
该运行的 workflow SHA 必须与源码提交一致，固定 run/attempt 的包在验收后直接提升，
不把 rc.3 包改名冒充 rc.4，也不在验收后暗中重建。
本次完整原生测试的实际通过、失败、跳过数量与产物身份在发布页面的验收附录中列出，
均取自上述新版本运行；历史专项和上一版本结果只作背景。

- CSV 构建选择包含两个真实测试可执行程序（49 个解析子用例、12 个路径 ABI 子用例）
  及四个显示辅助进程。要求选择集合完整且全部成功，不将“未选中”误当通过。
  ABI 回归逐一比较全部合成数值与时间戳。
- 最终 Windows IFW 原包实际安装并检查内嵌版本、19 个插件、Python、
  公共测试 BIN 中文路径的 1,940 条数值序列、曲线样本和恢复，然后卸载。
- AppImage 与 DEB 原包分别在无构建树的 Ubuntu 22.04 / 24.04 环境运行：
  校验 21 个插件的包内清单，实际加载其中 20 个。
  ROS 2 插件仍随包，因干净环境没有 ROS 2，运行功能明确未验收。
- 五次验收是 Windows 安装器一组，加两种 Ubuntu 各自的 AppImage/DEB 四组；
  每组覆盖 ASCII/中文 CSV 路径 × 英文/简中，共 20 组完全合成 CSV 宿主导入。
  每组检查两个字段、全部三个有限且可见样本、精确极值/时间范围和视口；
  宿主层不声称逐个内部数据点比较，该比较由插件 ABI 测试完成。
- 公共 BIN fixture 的截断尾记录警告保留，不将其改写成无警告样本。
  包验收要求没有未绑定曲线或错误级诊断，并检查可见有限采样和非默认视口。
  中英文最终截图检查文字和曲线，不只依赖非空导入消息。
- 发布前核对源/tag、版本映射、SDK/插件来源、实际载入 DSO 与原包哈希；
  草稿上传及公开后分别重新下载，对齐资产名称、大小、SHA-256 和已验原包。
  详细报告、截图及来源文件保留在 CI 工件和包内，不额外堆入下载区。

主程序使用 Qt 6.11.1、C++20、PlotJuggler SDK 0.34.1，Windows 使用 MSVC 194。
不同重建插件仍使用各自固定 SDK 0.20.0、0.32.0 或 0.34.1，不相互替换。
CSV 源码固定于 `PlotJuggler/pj-official-plugins` 的
`ba6ee417d91a01aae778a0ec3a4443a024671123`（`data_load_csv/v1.0.7`），
SDK 0.34.1 源标签提交为 `4d59e7de81455afe73a77051075e8fb4b9f6b0fd`；
Conan 二进制依赖和源码回退是不同获取方式，实际使用的 recipe/package revision
由本次构建来源图记录，不把回退 SHA 冒称实际重建了 SDK。
锁文件、许可证及重建身份记录位于包内 `release.json`、`share/licenses` 和对应 CI 工件。

此前独立源码复核、集成复核及其当时的限制原样保留于：
[源码报告](../../blob/@SOURCE_SHA@/docs/localization/CSV-UTF8-SOURCE-REVIEW-20261026.txt)、
[集成报告](../../blob/@SOURCE_SHA@/docs/localization/CSV-UTF8-INTEGRATION-20261026.md)、
[独立集成复核](../../blob/@SOURCE_SHA@/docs/localization/CSV-UTF8-INTEGRATION-INDEPENDENT-REVIEW-20261026.txt)。
它们不替代本次新版本的最终原包验收。所有可公开复现数据均为合成输入或公开上游 fixture，
不包含私人飞控记录或其衍生数据。

## 兼容性与已知限制

- Mosaico 1.3.0 明确保留官方原始二进制及部分英文；限定的静态显示翻译仍在，
  混合用户/服务器正文不做猜测替换。其独立 SDK 重建再分发许可依据仍需核实，
  跟踪 [#20](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/20)。
- Qt6/PJ4 插件 ABI 与 Qt5/PJ3 不兼容；BIN 使用 bootstrap ABI 5 / data-source ABI 4。
  4.x 不保证完整兼容 3.x 布局文件，建议并行安装并保留备份。
- Linux 主程序及普通插件的 glibc floor 为 2.35，实测包环境为 Ubuntu 22.04 / 24.04 x86_64；
  ROS 2 distro-specific inner 需要匹配并 source 外部 ROS 环境，不由普通包验收证明。
- Windows 原包在 Windows Server 2022 x64 runner 安装、启动、加载插件及卸载。
  Windows 未进行人工可见桌面目视验收；离线截图和自动断言不能扩展为 Explorer、
  全部安装页、快捷方式或所有 Windows 10/11 用户配置的人工实测结论。
- 没有 macOS、ARM 或 WebAssembly 发布包；WebAssembly 不启用原生 BIN 共享插件。
- 安装器未签名；语言切换依赖 PowerShell/CIM，受系统策略限制时可正常退出后
  手动以 `--lang zh_CN` 或 `--lang en_US` 启动，不要求修改系统安全策略。
- 动态路径、数据字段、插件 ID、第三方错误及用户/模型生成内容可能保留原文；
  APBIN 网站入口补全和 FFT 完整汉化不在本次源码中，不能宣称插件全部中文。
- SDK 没有旧版逐字段 tooltip setter，字段说明继续保留在数据集元数据；
  详情见 [BIN SDK4 说明](https://github.com/reliable-ly0411/plotjuggler-apbin-plugins/blob/@BIN_SHA@/sdk4/UPSTREAM.md)。
- 3.x 历史启动图像问题 [#3](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/3)
  及 Qt5 PR #6 不属于本候选验收，不因此关闭或声称解决。

应用为 MPL-2.0；独立 BIN 为 LGPLv3；SDK 保持 Apache-2.0；
Qt、官方插件和字体按各自许可分发，许可文本与对应源码链接随包保留。

## 原包校验

@ASSET_TABLE@
