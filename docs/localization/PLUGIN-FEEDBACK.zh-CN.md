# 已安装插件元数据与 FFT 1.0.1 显示修复

这是尚未发布的独立开发候选。原补丁基于繁中提交
`aea5767b1a1cbd2fa2327a135cb7df5326fa0b6c`，当前本地整合基于开发线
`1f71f9a0dec64e54b474669808bbff0d5ede5811`，保留上述繁中历史及开发线已有的 CSV 修复。
不修改稳定线、已发布包或插件 ABI。

## 根因及修复范围

APBIN 1.2.0-pj4.rc.1 的嵌入清单已有作者、许可证和仓库地址，但 SDK 0.34.1
的发现描述符、宿主已安装记录和检查辅助进程投影没有这些显示字段；市场的本地独有行
因此也没有网站入口。宿主现在通过 SDK 已验证的公开 family loader 补取同一 ID/版本的
嵌入清单，并将四个显示字段贯穿 helper、扫描记录和市场详情。目录缺省字段可由本地记录
补齐，目录已有字段仍优先；URL 先 `website` 后 `repository`，两者为空则隐藏入口。
不读 sidecar 作为显示权威，不硬编码 APBIN，不改变下载、版本或校验和判定。

FFT 市场详情和实际工具界面使用不同显示路径。固定随包映射没有覆盖后装官方 FFT 1.0.1，
并非已经证明市场更新覆盖了汉化插件。新增宿主显示映射和简中/繁中目录，覆盖工具名称、
说明、面板标题、输入/范围/窗口/输出控件、图表标题与拖拽提示、计算/导出状态及已知错误。
面板仅接纳经过审阅的 UI 哈希、控件名、属性和固定原文；未知 UI 哈希或未匹配的文案
保留原值。面板识别不接收版本号，其他版本若 UI 字节完全相同也会使用该显示映射；
工具菜单的名称和说明另按插件 ID、版本及固定原文匹配。

带变量的状态仅匹配指定状态标签的完整模板。用户字段、外部错误详情、数字格式、`s`、
`Hz`、`_FFT`、`hann`/`rectangular` 和 `frequency_hz`/`amplitude` 不改变。
`selected_value` 的 “No input selected” 可能与数据名相同，必须由同批状态明确禁用计算
按钮才能翻译，不能使用旧控件状态推断。语言仍遵循应用现有重启生效约定。

## 原始插件来源

- 官方仓库：`PlotJuggler/pj-official-plugins`。
- tag：`toolbox_fft/v1.0.1`；提交：`2bc991cae2dba7f9f1468dbf8dd72d89797699bc`。
- 原始 `toolbox_fft/fft_dialog.ui` 的 LF SHA-256：
  `f7d484492d4b2033fc141c9ea3a9f83e9a976049947ba9dd90079df2d19099c0`。
  fixture 原样保留，许可证与来源见 `pj_dialog_host/tests/fixtures/`。
- Linux 官方 ZIP SHA-256：
  `038d290152deb4ab6e1abfb088a1b44792e5d55262994e0ecd73ed26803eb87a`。
  验收使用原包 DSO，不使用新 SDK 重编它（该插件源版本记录的 SDK 为 0.20.0）。
- 宿主仍为 SDK 0.34.1，源码 tag `v0.34.1`，提交
  `4d59e7de81455afe73a77051075e8fb4b9f6b0fd`。

## 可重复回归

基础语言专项入口仍为 `pj_app/tests/i18n`。市场专项可独立编译，只使用隔离配置、临时仓库
及合成 fixture；URL 点击被进程内接收器截获，不启动浏览器。fixture 构造函数故意中止，
用来验证直接 vtable 发现没有实例化插件。伪造 sidecar 不覆盖嵌入清单。

```sh
cmake -S pj_marketplace/tests/metadata -B build-plugin-feedback \
  -DCMAKE_PREFIX_PATH='/path/to/qt;/path/to/dependencies' \
  -DPJ_SDK_SOURCE_DIR=/path/to/unchanged-sdk-0.34.1 \
  -DPJ_FFT_TEST_PLUGIN=/path/to/verified-official/libtoolbox_fft_plugin.so
cmake --build build-plugin-feedback
QT_QPA_PLATFORM=offscreen \
PJ_APBIN_TEST_DIR=/path/to/existing/apbin-package \
PJ_TEST_SCREENSHOT_DIR=/path/to/isolated/screenshots \
ctest --test-dir build-plugin-feedback --output-on-failure
```

不提供 `PJ_APBIN_TEST_DIR` 时，仅真实 APBIN 副本用例明确跳过；通用元数据用例仍运行。
不提供 `PJ_FFT_TEST_PLUGIN` 时，不构建可选 FFT 二进制验收。测试不下载安装插件。
Qwt 使用仓库原有固定版本；离线时可传入已验证源码的
`FETCHCONTENT_SOURCE_DIR_QWT_UPSTREAM`。

FFT 验收加载官方原始 UI，使用生产 `PjUiLoader`、显示映射和 `ChartPreviewWidget`，
通过真实 Toolbox/Dialog ABI 输入纯合成信号。测试驱动仅实现 FFT 所需的 widget-data
应用子集，不替代完整 `PanelEngine`/`MainWindow` 事件链。覆盖简中→繁中→英文的重新加载、
初始/计算/导出和错误画面，断言 128 样本、65 频谱点、62.5 Hz 峰值和 2.0 幅值及导出列。
菜单使用生产名称/说明映射构造 QAction；完整主窗口交互由下面的宿主验收独立覆盖。

普通语言专项还验证全部已登记静态文案、完整模板与用户数据占位符、错误上下文、CRLF
身份、未知 UI 和同名输入保护。`WidgetBindingLabel.FftEmptySelectionUsesSamePayloadState`
纳入完整 dialog-host runner，验证真正的 QLabel 绑定及过期控件状态。

完整构建可开启 `PJ_PLUGIN_FEEDBACK_ACCEPTANCE=ON`，再构建 `pj_app`、
`plugin_feedback_test`、`pj_dialog_host_tests` 和 `plugin_display_metadata_test`。
将经过校验的 APBIN 已安装包副本与官方 FFT 包副本放入同一目录的独立子目录：

```sh
QT_QPA_PLATFORM=offscreen \
PJ_FEEDBACK_PLUGIN_DIR=/path/to/verified-plugin-copies \
PJ_GUI_ACCEPTANCE_DIR=/path/to/isolated/screenshots \
ctest --test-dir /path/to/full-build -R '^PluginFeedbackMainWindow-' --output-on-failure
```

该 runner 链接与主程序相同的 `pj_app_shell`，每种语言使用新进程、新 profile。
它把插件副本复制到该 profile 的托管目录，并位于无随包插件目录的位置，防止随包
seeding 掩盖本地安装场景。使用空目录清单验证真实市场详情、作者、许可证及网站动作；
真实 Toolbox 菜单启动 `PanelEngine`，拖入主窗口生成的正弦数据，点击计算、导出，
断言原始列名实际进入数据树。还通过主窗口打开首选项，保存简中→繁中→英文→简中
选择，核对运行中界面保持原语言以及保存后的偏好值。每个进程的初始语言也从
保存偏好读取；语言行为仍是重启生效，不是热切换。

## 本机验证边界

2026-10-26 Ubuntu / Qt 6.11.1：真实市场窗口、APBIN 已安装副本、FFT 官方 Linux DSO
的上述专项与离屏截图通过。截图人工检查涵盖简中、繁中、英文，使用合成信号；未使用用户日志。
两份目录各 2,020 个源键，无缺失、过期、未完成条目。完整主程序、真实主窗口验收
runner 和完整 widget binding runner 均已编译、链接并通过下述检查。
Windows、macOS、WebAssembly、安装/维护和最终发布包均未由本轮验证。没有修改用户安装。

本机最终检查：Qt 语言专项 26/26；市场/FFT 专项 2/2；固定 APBIN 解析与动态 ABI
专项 2/2；Python 源码回归 119 通过、5 项 Windows 专属检查跳过；发布策略 4/4。
分支命名、来源与固定 gitlink、翻译生成一致性及 `git diff --check` 均通过。

完整构建使用项目隔离 venv 的 Conan 2.33.0、项目缓存、仓库锁文件及官方源，Release、
测试开启、演示关闭、无调试信息，单任务编译。Qt 6.11.1、SDK 0.34.1 与 Qwt 6.3.0
保持固定版本。`pj_app` 完成 501 个构建步骤并成功链接；没有修改系统 Python 或已安装程序。
完整主窗口三语言验收 3/3、dialog-host 168/168、市场显示元数据 1/1、
`ExportedSymbolsGuard` 1/1 通过。人工查看了三语言真实主窗口、网站详情、FFT 菜单、
初始/计算/导出及首选项截图，未发现缺字或文字截断。首次主窗口测试的两项失败来自
验收代码错误地用正文翻译上下文查找菜单；改为元数据上下文后复测通过，未为此修改产品代码。

本地验证配置有两项明确边界，仓库依赖文件未改变：系统缺少 `libva-dev`，因此仅此次
Conan 调用设置 `ffmpeg/*:with_vaapi=False`；elfutils 源码依赖不可用，使用配方支持的
`backward-cpp/*:stack_details=backtrace_symbol`。
因此视频 VAAPI 硬件解码和崩溃报告的源码行号符号化不在通过结论内；主程序模块均参与构建。

## 2026-10-27 Ubuntu 复核补充

现有完整构建与产品源码保持一致；构建系统确认 `pj_app`、真实主窗口验收、dialog-host
和元数据测试目标没有待编译的产品变更。本次新增的只是元数据测试及本文的验证记录，
没有改动 SDK、插件二进制或产品实现。

市场回归新增 18 个数据行（6 种情形 × 英文/简中/繁中）：网站优先于仓库、空白网站
回退到修剪后的仓库地址、地址均为空或均为空白时隐藏入口，以及目录已有网站、仓库、
作者和许可证保持优先。点击仍由进程内 URL 接收器截获。连同原有用例，Qt 输出为
28 通过、0 失败、0 跳过，其中含初始化及清理；不能将 28 当成 28 个独立产品场景。

重新执行的完整宿主相关 CTest 为 172/172：dialog-host 168、三语言真实主窗口 3、
导出符号检查 1。完整宿主构建中的元数据 CTest 另为 1/1。独立市场/官方 FFT 二进制
CTest 为 2/2；其中 FFT 的 Qt 结果是三语言场景 3 加初始化/清理 2，共 5 通过。
所有这些本轮重跑均无失败或跳过。实际 APBIN 副本用例已启用，没有用未设置目录的
跳过结果代替验证；插件 DSO 摘要与前次核验记录一致。

本轮另检查了新生成的简中 APBIN 详情、简中 FFT 导出、繁中 FFT 计算、英文 FFT
初始画面四张真实主窗口截图；作者、许可证和网站入口可见，已查看区域无缺字或截断。
所有数据来自测试程序生成的正弦/余弦信号。其余本轮截图已生成，但不扩大为全部重新
目视审查的结论；2026-10-26 的目视范围见上文。

上述复核对应 `aea5767b1a1cbd2fa2327a135cb7df5326fa0b6c` 基线，保留先前繁中提交。
该次复核时尚未与后续开发线的 CSV、rc.4 提交整合，也尚无本修复的独立源码审查结论。
Windows/MSVC、macOS、WebAssembly 或最终发行包未在该次复核中验收。
源码补丁、独立审查、维护分支集成和新版本发布须分别记录，不能用本机专项通过代替
尚未进行的阶段，也不能据此改写已发布 rc.4 的内容或身份。

## 2026-10-27 独立源码审查与开发线整合

独立源码审查通过的原补丁为 181,240 字节，SHA-256：
`a8ec4d14ebbd3c970a6929bcc1e29ef825a8605c1d838b8bce4d10103f0045fb`。
审查核对 SDK loader、Dialog tail-slot/handle 生命周期、辅助进程边界、动态文本和数据
语义，未发现阻断产品缺陷。独立执行的显示映射源码测试为 6/6，两份翻译目录结构及
繁中/开发两侧源码锁摘要通过；这些检查不等同于独立重新构建或运行主程序。

本地整合以开发线 `1f71f9a0dec64e54b474669808bbff0d5ede5811` 为 HEAD，待合并父提交为
繁中基础 `aea5767b1a1cbd2fa2327a135cb7df5326fa0b6c`，当时尚未提交。源码锁同时保留繁中
helper 和既有补丁摘要、CSV 原子修复及其完整来源记录。CSV CTest 精确集合增加
`LocalizedDisplay_zh_TW`，仍要求两个 parser/path 测试与全部五个显示测试过程。
离线回归直接运行真实 builder 至 CTest 调度边界，验证完整集合通过，以及缺繁中、
缺路径测试、额外测试三种集合均拒绝；外部下载和构建命令以受控替身代替。

本次完整主程序、插件检查 helper、真实主窗口验收 runner 和相关回归目标已在该独立
工作树编译、链接成功，使用 Ubuntu 24.04、GCC 13.3、Qt 6.11.1、SDK 0.34.1。
沿用上文披露的本地依赖选项，未改变仓库的依赖锁或版本文件；新主程序的 `--version`
退出码为 0，返回 `4.0.0-zh.1.rc.4`。这是该基线上的未提交本地构建，不是已发布 rc.4 资产。

整合后的实际执行结果：

- 完整宿主相关 CTest 173/173：dialog-host 168、三语言 MainWindow 3、元数据 1、
  导出符号检查 1。JUnit 内部输出无 fixture 跳过，元数据 Qt 汇总为 28 通过、0 失败、
  0 跳过（含初始化/清理）；真实 APBIN 副本用例已执行。
- 市场/helper/ExtensionManager 及 BIN 相关 CTest 108/108，无失败或跳过；其中 BIN
  解析和动态插件 ABI 占 2 个 CTest，未使用私人飞控日志。
- Qt 语言专项 26/26。首次有 4 项因执行环境无法监听本机回环 HTTP 夹具而失败；
  在具备该监听能力的环境中仅重跑该 4 项并全部通过，未修改产品或放宽断言。
- Python 127 通过、5 项 Windows 专属检查跳过；发布策略 4/4；分支、来源、固定
  子模块、源码锁摘要和 `git diff --check` 通过。两种中文各 2,020 条源消息，提取集合
  无缺失、过期或未完成；占位符、复数和富文本检查通过。

本次人工查看全部 18 张新真实主窗口截图：每种语言各含 APBIN 详情、FFT 菜单、初始、
计算、导出及偏好窗口。作者、许可证和网站按钮可见；未发现缺字或截断。图表和导出
状态来自主窗口生成的合成信号；数据字段、单位和 `_FFT` 保留原值。网站动作由进程内
URL 接收器验证目标地址，不启动外部浏览器。语言选择按已保存偏好在新进程加载，
当前进程保持原语言；这不是热切换测试。完整宿主断言验证计算/导出状态及列进入数据树，
不把它扩展为逐点频谱数值等价验证；专用 FFT ABI 数值验证的历史范围见上文。

整合源码独立复核确认：原 APBIN/FFT 产品代码与已审查补丁一致；繁中和 CSV 的锁记录
完整保留；新增 builder 回归能检出恢复旧缺失繁中集合和删除严格集合断言两种变异。
独立执行 builder 回归 7/7、显示映射回归 6/6、两语言目录结构及锁摘要检查均通过。
这些独立检查与本机运行证据分开计数，不代表独立重新执行了完整主程序或截图验收。

Windows 原生构建、完整多平台插件重建、安装器及发行包验收仍须另行执行。
独立审查没有新增专门的旧 Dialog 缺 tail-slot/null-create/destroy-order 或 MessageParser
元数据 fixture；对应生命周期目前为源码核对，不宣称已通过 sanitizer 或专门运行回归。

## 2026-10-28 候选构建与验收接线

候选保留繁中提交及开发线的真实历史，将上述修复与原生/包级验收入口一同提交。
这不改变已发布 rc.4 的标签、正文或二进制。候选沿用开发分支当前版本号；
仅凭文件名或 `--version` 不能把候选包视为已发布 rc.4，必须同时核对其
`release.json` 的源码提交、源码树及对应 Actions run/attempt。

原生构建显式启用三语 `PluginFeedbackMainWindow-*` 和显示元数据用例。
输入准备只接纳当前构建由 CMake 选定的 APBIN 与锁定哈希的官方 FFT 1.0.1，
分别记录来源和文件摘要，既定 Windows 19 / Linux 21 个随包插件清单不扩大。
结果守卫拒绝缺失用例、JUnit/Qt 内部失败或跳过、缺少真实流程 PASS，以及缺少
18 张三语截图；PNG 结构和摘要检查不能替代人工像素审阅。

最终包 CSV/BIN 验收新增繁中进程、截图及报告检查；安装后 APBIN 详情和 FFT
交互仍是另一个验收阶段。IFW 向导仍仅简中/英文，Mosaico 例外保持不变。
正式 payload 暂存要求干净的已提交源码，不允许用 HEAD 身份标记未提交修改。

接线补丁的离线回归为 16/16，原有包验收辅助测试 26/26、发布规则 4/4 通过；
独立审查另执行相同 16 项离线测试并通过，没有发现阻断接线的源码缺陷。
整合候选随后运行完整 Python 源码检查：148 项中 143 通过，5 项 Windows 专属
检查跳过；发布规则 4/4、两份 2,020 项目录结构及来源/固定子模块检查通过。
此次目录结构检查没有重新提取源键，完整 `lupdate` 检查由原生构建执行。
这些结果验证辅助脚本及规则，不能替代本候选的完整 Linux/Windows 构建、
全部锁定插件重建、最终安装包或截图验收。实际平台结果以同一候选提交的
Actions 记录为准，历史 Linux 结果不算作本候选的 Windows 通过证据。

首轮候选 CI `40697391495`（源码/工作流 `59c5b70ad7aaa4e149a06002e6210fdfe9a25d98`，
attempt 1）的 Linux 和 Windows 完整编译在 `pj_bundled_translations_test` 失败：FFT 回归直接使用
`QDomDocument`，但完整工程中的该测试目标未声明 `Qt6::Xml` 依赖，因而缺少对应头文件
搜索路径。独立语言测试入口已声明该依赖，其通过不能覆盖此构建接线遗漏。
后续修复为完整工程的测试目标补齐直接依赖；Qt 版本、产品实现及测试断言保持不变。
新的完整候选运行仍须独立完成，不能把该失败运行记作平台验收通过。

第二轮候选 CI `40706607112`（源码/工作流
`a8ffa5ccb3762f7e1244350953094570e58b29e9`，attempt 1）双平台完整编译通过，
但原生验收步骤暴露两处流程问题，后续插件重建和最终包验收均未运行：

- Linux CTest 共 3,480 项，0 失败、38 跳过。必需的元数据和三语主窗口四项均运行；
  完整日志中元数据 Qt 汇总为 28 通过、三语主窗口各 3 通过（含初始化/清理），均无
  失败、跳过或黑名单，且包含真实流程 PASS 标记。JUnit 成功输出被 CTest 默认
  1,024 字节上限截断，丢失尾部汇总，严格证据守卫因此拒绝通过。
- Windows 在新增的 `--show-only=json-v1` 枚举阶段，PRE_TEST 启动
  `pj_scene2d_core_source_dir_tests.exe` 返回 `0xc0000135`。该命令位于既有
  FFmpeg/Python DLL 搜索路径准备之前，完整原生测试尚未执行。

流程修复将 Windows 运行库路径初始化放在枚举前，并在两平台将成功用例输出的
保留上限设为 256 KiB。证据守卫额外明确拒绝 CTest 截断标记，仍要求实际流程 PASS、
唯一完整 Qt 汇总及零失败/跳过/黑名单，不修改产品代码或放宽断言。

定向辅助回归现为 20/20：新增测试使用真实 CTest 和纯合成 runner，复现 1 KiB
截断及缺少运行库路径的枚举失败；执行两份实际 workflow 的 Linux/Windows shell
分支，验证环境顺序、完整 JUnit 与 18 张合成 PNG 的证据检查。路径转换和 GUI 包装器
为受控替身，没有运行原生插件或 Windows DLL，不能视为 Windows 平台通过。
后续必须以新提交的完整 CI 及最终包验收确认修复。

第三轮候选 CI `40718926632`（源码/工作流
`54e021c0c0980e124c4fef5e7e591320400a1d7b`，attempt 1）Linux 原生测试、严格证据
检查、固定插件重建及候选打包通过。Windows 完整编译和 CTest 执行完成，共 3,474 项，
0 失败、74 跳过；但四个必需 Qt 用例的 JUnit 和 `LastTest.log` 输出均为空，证据守卫
正确拒绝，不能据退出码或截图推断 Qt 内部零跳过。下游干净环境与最终清单验收未运行。
同轮既有翻译测试的显式文件日志包含完整 Qt 汇总，而其控制台/JUnit 输出仍为空；
仅增加 stdout 日志选项不足以证明解决此环境的证据缺失。

后续仅为这四项验收增加共享 CMake/Python 日志包装器：每次调用创建独占临时目录，
要求真实 Qt 子进程写入文本日志，并将原始字节转入 CTest 输出。不存在或为空的日志
即使子进程退出码为零也失败；非零退出、超时仍失败。子进程期限比既有 CTest 外层
期限短 5 秒，用于终止、回收直接子进程及保留部分日志；不读取旧工作目录日志。
结果守卫、256 KiB 保留上限及运行库初始化顺序保持不变。

此轮定向回归 26/26：5 项真实子进程检查覆盖原始字节、环境/目录、重复执行隔离、
缺失/空日志、旧日志、失败退出和超时；21 项原有/扩展验收接线回归使用实际 CMake
函数、CTest 和 workflow shell。纯合成 runner 仅写文件、控制台无输出；直接运行时
复现证据拒绝，通过包装器后仍须满足原有严格断言。这不是新 Windows Qt 执行结果，
下一轮精确提交的原生构建与包验收仍为必要门槛。
本地完整 Python 辅助检查为 158 项中 153 通过、5 跳过，发布策略 4/4 通过；
没有重新构建完整主程序，也没有把合成日志包装器测试计入原生 GUI 通过数。

第四轮 `40731661989`（源码/工作流 `c016dca1c51d333771bad129230926ed3ff69ee4`，
attempt 1）Windows 轻量预检发现新增夹具的生成器选择错误：在 Windows 默认的
多配置生成器下模拟 Linux shell，没有传入配置，四项 CTest 均未运行，严格断言失败。
5 项子进程日志测试在该 Windows 预检中通过；本轮未进入 Windows 主程序构建。
后续将这个同时模拟两平台的夹具显式固定为 Ninja 单配置，并另以真实
Ninja Multi-Config 加 `-C Release` 验证共享日志函数。没有修改生产 workflow 的
配置选择或过滤这些失败；新的 Windows 预检及完整候选结果须重新确认。
