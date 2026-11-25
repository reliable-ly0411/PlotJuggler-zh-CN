# 4.x 上游同步开发快照（2026-11-08）

## 来源与范围

- 开发输入：`82a787414217e32638f257e02fdb03d8d08d477a`，包含已合并的 #39 拖入安全保护及 #40 文档。
- 原上游基线：`349c74e3b0ada0081b7d0006e729de66e8e3b6e5`。
- 新上游 `main-4.x`：`0511b57bb1806b08c1ee3fee60d96c1e0448c358`。
- 官方 `4.1.0` 标签对象：`da079f6670d3a1873ed1011dedc15556e6f838de`；指向提交 `1b8fb491f56cc185ae395e2c7a0561443ad18d07`。
- 新快照在官方 `4.1.0` 之后有 19 个上游提交；本轮相对开发输入增加 5 个，并用普通双父合并保留真实祖先。
- 开发版本：`4.1.0-zh.1.dev.2`；Qt `6.12.0`；宿主 SDK `0.39.0`。

本轮新增上游：

| 提交 | 范围 |
|---|---|
| `08aa99c2` | 恢复主窗口关闭时的位置、大小与最大化状态；Wayland 仍由合成器控制位置 |
| `a0956b20` | 日期时间显示、时钟时区设置，以及移到左下方的时间偏移开关 |
| `092bcfa2` | 测试默认不在当前桌面打开窗口，真实显示测试须显式选择 QPA |
| `b0cd6fca` | 插件标签改名同步更新标签栏 |
| `0511b57b` | 浏览器选取的数据文件流式写入 MEMFS，避免完整复制到 WASM 堆 |

这是未发布开发快照，不是官方 `4.1.0` 原始源码，也不是已经验收的汉化发行包。
既有发行标签、包字节、旧发布说明和历史覆盖数量不变。独立 `4.1.0` 发行准备不属于本轮同步；
不合入上游贡献分支，不改写上游镜像，不自动晋级稳定线、创建标签或发布。

## 本地化与合并处理

主窗口工具栏只有一处内容冲突：采用上游时间偏移按钮迁移，保留参考线提示的可提取标记。
时间偏移提示现在在 `TimelineWidget` 上下文中翻译；旧 `PJ::MainWindow` 条目不再有效。
Copy-only 拖入、事件返回后排队导入、MIME 生命周期与源文件保留测试保持不变。

简中、繁中各含 **2,100 条有效 Qt 可提取消息**，比上一轮 2,093 条净增 7 条。
8 条需要处理的目录项含 1 条上下文迁移、时区/日期时间显示和浏览器读取错误。
`UTC` 与 `HH:mm:ss` 保留技术格式，动态文件名不参与翻译；语言切换不修改数值解析 locale。
新增语言回归检查两个中文目录的实际运行时上下文、旧上下文回退、格式和文件名占位符。

浏览器选择器 `EM_JS` 中两个 JavaScript 空字符串使用等价的双引号形式，以兼容 Qt 6.12
`lupdate` 的 C++ 扫描器。新文件暂存/读取错误使用明确的 Qt 翻译上下文，读取、取消、对象 URL
回收和租约行为保持上游实现。源码提取与 native 编译不等于 WASM 流式导入运行验收。

## 测试与权限边界

#1479 移除了自动选择真实显示平台的逻辑。初版同步给完整 native 调用显式选择 Linux
`xcb`（私有 Xvfb）或 Windows `windows`。Windows 覆盖所有普通 widget runner 的范围过大，
首轮精确 CI 及修正见下文。当前 Windows 普通组清除外部 `QT_QPA_PLATFORM`，由共享 GUI main
默认选择 offscreen，独立 main 或 CTest 自带环境保持各自行为；QRhi 与主窗口原生生命周期
分别使用 `windows`、WARP 和 GPU 硬门禁。Linux 已验证的 `xcb` + `PJ_REQUIRE_GPU_TESTS=1`
不变，没有把 GPU 失败降级为跳过。独立 i18n、Qt-only 和指定 offscreen 的 CTest 用例、
X11/Wayland 专项保持原环境与触发边界。

工作流权限、原生构建手动门禁、包验收和发布触发条件不变。普通 topic/dev push 和 PR
只运行 source checks；完整双平台开发 CI 由 `zh-4x-ci.yml` 显式手动调度，或首次创建
`zh-CN-4.x-ci/manual-build-<唯一标识>` 指向精确待验提交来触发。该工作流仅测试并保存报告，
不创建标签、Release 或生产安装包；本轮不运行 `zh-4x-publish.yml`。

## 同步初版本地验证

- Qt 6.12.0 `lupdate`：简繁各 2,100/2,100，缺失、过时、未完成均为 0；占位符、复数、富文本及上下文通过。
- Python source 回归：179 项，169 通过，10 项平台/可选环境测试跳过。
- 发布策略：5/5；源码同步策略：8/8。新增 3 项显示平台边界回归包含在 source 回归中。
- Qt 6.12 独立语言、插件显示、目录、配置、资源及安装器脚本套件：26/26 通过。
- 上游原有 `TimeFormat` 8 项及 `FileSelectionServiceTest` 4 项：生产源严格编译并通过 12/12；仅 native 路径。
- DataFlash 独立解析器：1/1 通过，包含固定真实 BIN 日志；不代表动态插件/全宿主 ABI 验收。
- UI 编译、Bash 语法、分支与差异检查通过。
- 全仓 pre-commit 检查遇到既有基线问题：固定来源补丁/历史夹具的空白，以及插件显示头中的 `std::getenv` 规则冲突。全仓格式化产生的无关变更已还原；本轮 68 个变更文件的全部适用 hooks 单独检查通过，未放宽规则。

本地工具链为官方 Qt 6.12.0、GCC 14.2.0、CMake 3.31.10。完整应用与 SDK 图不在上述专项构建中。

## 后续精确提交验收

完整 `zh-4x-ci.yml` 必须针对本候选的精确 SHA 在 Linux/Windows 运行，保留 source、语言、
完整 native、BIN/FFT/三语反馈 GUI、Windows PE/重定向 CLI、GPU 和 X11/Wayland 报告。
重点复核新增时间格式、插件标签改名、窗口几何恢复，以及既有文件拖入安全回归。
以实际 JUnit/截图和通过、失败、跳过数量为准，旧 SHA 的成功不替代新快照结果。

本地没有进行完整宿主构建、真实桌面视觉检查、Windows/D3D、macOS/Metal、浏览器流式大文件
运行或最终原包安装验收。WASM 须另外执行固定 Emscripten 工具链构建及
`tests/wasm/ingress_file_selection.spec.js` 等浏览器检查，不能由 native 12/12 推断通过。
稳定晋级仍须审阅后使用普通 merge，保留稳定线自身未进入开发线的提交；最终包/发行是独立门禁。


## PR #42 首轮原生 CI 与 Windows 修正

首轮固定源码为 `39bc927997918bfb399bef08ed12c20ea62bf01b`，tree
`1864410f86c3f949721b8bb19c438024060424c9`，
[CI run 42438013105](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/42438013105)。
原始 JUnit 记录：

- Linux 全量 native 5657 项：5555 通过、102 跳过、0 失败；X11/Wayland 窗口专项各2项通过。
- Windows 全量 native 5372 项：5267 通过、103 跳过、2 失败。
- 两平台的7项 FileDrop 与2项 MainWindowRhiWindow 均实际执行，不是跳过；Windows 没有GPU用例大面积跳过。

两条 Windows 失败不能用删除断言或转为跳过处理：

1. `WidgetBindingMarkdown.RendersGitHubMarkdownUnicodeAndBlocksEmbeddedResources` 假定请求字体为
   字面 `monospace`。Qt 6.12 的 [Markdown importer](https://github.com/qt/qtbase/blob/v6.12.0/src/gui/text/qtextmarkdownimporter.cpp#L115)
   实际取 `QFontDatabase::systemFont(FixedFont)`，并在[代码块应用该字体](https://github.com/qt/qtbase/blob/v6.12.0/src/gui/text/qtextmarkdownimporter.cpp#L645)。
   修正为精确比较非空的系统 fixed-font families，而不是接受任意字体或检查环境解析后的 `QFontInfo`。
2. `FileDialogStartFolderTest.PersistedQtMemoryDropsLastVisitedAndDeadShortcuts` 暴露真实初始化顺序问题。
   Qt native helper 存在时，[setHistory](https://github.com/qt/qtbase/blob/v6.12.0/src/widgets/dialogs/qfiledialog.cpp#L1897)
   和 [setSidebarUrls](https://github.com/qt/qtbase/blob/v6.12.0/src/widgets/dialogs/qfiledialog.cpp#L429) 不应用到 widget。
   [DontUseNativeDialog](https://github.com/qt/qtbase/blob/v6.12.0/src/widgets/dialogs/qfiledialog.cpp#L796) 才创建 widget 树。
   本仓提前设置该选项，再恢复已过滤的 history/sidebar；原来“保留可达项、删除死链接”的断言不变。

Windows 开发与候选打包流程采用三个互斥且完整的主测试分组：

- 普通组：`env -u QT_QPA_PLATFORM`、`-LE qrhi`，排除 `MainWindowRhiWindowTest`。
- QRhi 组：`windows` + `QSG_RHI_PREFER_SOFTWARE_RENDERER=1` + `PJ_REQUIRE_GPU_TESTS=1`，`-L qrhi`。
- 主窗口生命周期组：同样显式 native 环境，`-LE qrhi -R MainWindowRhiWindowTest`。

原始完整发现清单与三份 JUnit 逐名称核对，无遗漏、重复或陌生用例；失败、错误、跳过、disabled
及完整已捕获 testcase 子树保留，矛盾计数/status 和损坏清单失败关闭。CTest 非零退出不能被一份
看似全过的 XML 掩盖。汇总仍使用 `native-tests.xml` 供原APBIN/FFT/三语反馈审计。

另有独立 native portability 报告，精确包含上述两失败和全部7项拖入（同时涵盖
`MainWindowFileDropTest` 与 `MainWindowFileDropLoadingTest`），必须9项实际执行、无失败/跳过，
并保留GTest成功证据。它重复验证平台可移植性，不混入主报告的全量唯一用例数。
涉及 `QtProject` registry 的 FileDialog fixture 只在一次性 CI / 隔离环境运行，不在用户常用Windows桌面执行。

修正后的本地证据：

- 完整 source suite 193项：188通过、5项真实平台限制跳过；包含真实CTest分组/报告与非零退出负控。
- 分组汇总11项、显示边界5项、反馈/工作流24项全部通过；真实CTest fixture覆盖pass/fail/return77/disabled及合法空串命令参数。
- 本轮非格式化hooks与实际C++改动行的clang-format检查通过；FileDialog.cpp既有显示映射范围仍有整文件格式债，未扩散格式化到无关代码。
- Qt6.12 + GCC14 编译实际 `FileDialog.cpp` 与原9个FileDialog测试，Linux offscreen 9/9通过；
  独立Qt Markdown fixed-font契约1/1通过。这不是Windows native修复已经通过的证明。

以上修正必须在新的精确提交重新运行双平台全量 native 和Windows 9项专项。
首轮Linux通过不能代替新头结果，Windows两个失败在新头实跑前仍视为待复验。
不因本地source/专项通过而晋级稳定线或发布。


### CTest 输出完整性补充

Windows 修正快照 `b08248dda46ea9d7c169824a137ee5a2aacbb461`（tree
`b3c24599306a5f0ac6fa88262bef38d8f8996ba4`）的9项 native 门禁已拒绝 CTest 实际截断标记
`[This part of the test output was removed ...]`。后续将同一检查前移到三组通用汇总，
对每个 testcase 的 stdout/stderr 均失败关闭，不修改正常失败、跳过或 disabled 的计数规则。

新增真实 CTest 3.31.10 负控：9个合成 runner 均退出0，XML记0失败，保留前缀
`[  PASSED  ] 1 test.`，但256字节限额移除了其余输出。通用汇总、native专项验证及命令行
均拒绝该报告；不能只凭成功前缀接受不完整证据。另覆盖stdout/stderr和正常、失败、跳过状态。
此前原始双平台JUnit没有该截断标记；旧报告的通过/失败/跳过数和testcase子树原样保留。

本次完整source suite为195项：190通过、5项既有平台限制跳过；聚合13/13、显示边界5/5、
反馈/工作流24/24、发行策略5/5通过。193项旧结果仍对应上一补丁，不被追加负控改写。
本次只验证报告门禁，不重复Qt编译，也不代表新头双平台native、真实Windows或最终包已通过。
