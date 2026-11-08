# 4.1.0 标签锁定集成

## 基线与历史

- 官方 tag：`4.1.0`，annotated tag object `da079f6670d3a1873ed1011dedc15556e6f838de`。
- 应用基线：`1b8fb491f56cc185ae395e2c7a0561443ad18d07`。
- 汉化来源：开发线 `82a787414217e32638f257e02fdb03d8d08d477a`，包含 #33 插件反馈、#39 同步及 #40 文档历史。
- 在独立发行主题分支中保留上述公开祖先，反向排除 tag 之后的应用增量，再保留当前汉化与发行契约。
  没有重写开发线、镜像或历史 tag；开发线的文件拖放安全修复继续保留在那里。
- 与稳定维护线通过普通 merge 晋级；发布该精确树的最终原包，不重用旧 rc.4 字节。

## 审查的 tag 后区间

以下14个上游提交属于开发线历史，不整体纳入4.1.0发行基线：

- `e2e22ce3ae0abe88523e716985c42afa61c20777`：fix(packaging): provide CMake compatible with pinned Qt
- `73f5e3d01facd11a6caa462c9f212abf8dbd811d`：fix(ci): publish a builder image owned by each repository
- `a8a8a70b7c8019debf5c75f59555067c407a225c`：fix(conda): retry publication from saved release artifacts
- `7daeb6ec67931b48193ceff2e053280a670bd0b8`：fix(plotting): keep the zoom when a legend click toggles a curve (#1467)
- `f7950d205ac123c2269c886ab32aa3a591fa2cd5`：fix(app): wrap long Diagnostics messages instead of eliding them (#1471)
- `4a56ada7f790ae61f0bf831cb42cc45fc19b0673`：build: default to -g1 line tables; keep the symbol table in Linux releases (#1468)
- `361cdf9064adb9fc0946da9c38c0b1902be3f4f1`：fix(app): build the Windows executable as a GUI-subsystem program (#1469)
- `b428b6d58972bff94d6ac48d05d6795b926ed7af`：fix(app): give the Windows executable an icon and version information (#1470)
- `53983e3795d8c7650bc9ee0a2a0bede46aa46a5d`：fix(widgets): never show a parentless ElidingLabel as a window (#1473)
- `721516434404d6d7c659b00c23a5edce79b961da`：fix(app): composite the main window through QRhi from its first show (#1472)
- `a3640d63d820f1ab1df2b01dbd9ac06142119545`：fix(packaging): bundle native Wayland support in Linux packages (#1466)
- `fda4e555dfbb0278a85041107a81148f792fddb2`：fix(app): load dropped files and offer the system file dialog (#1474)
- `4b7ec5f04199b818058982642c32c8c0eba39158`：feat(packaging): build a macOS arm64 app bundle and disk image (#1475)
- `349c74e3b0ada0081b7d0006e729de66e8e3b6e5`：fix(app): defer dropped-file loads and take file drops as a copy (#1476)

其中 Windows GUI 子系统、图标及重定向 CLI 已是汉化发行的既有契约。
本次保留单一资源生成器、完整内嵌版本和 core-only 控制台安全处理，作为明确的发行补丁。
它们不意味着整体纳入对应上游之后的功能。没有保留文件拖放、系统文件对话框开关、
原生 Wayland 包装、macOS bundle/DMG、主窗口首次QRhi组合以及该区间其他通用行为改变。

`release-4.1.0-baseline-files.json` 记录该区间触及的52个路径：29个路径逐字节等同tag或同样不存在，
其余23个是有意保留的汉化/插件/构建与发行差异。所有 `sha256` 字段均指向官方 tag 字节（非候选摘要），测试对未修改路径执行固定SHA-256与缺失检查。
这不是“所有文件都等于上游”的声明：中文翻译、插件、版本和独立验收原本就是本分支差异。

## 保留的本分支能力

简繁/英文界面、当前2,091条双目录、固定市场和插件显示映射、FFT反馈修复、CSV UTF-8路径补丁、
BIN独立共享插件、独立profile与来源保护均保留。数值解析与稳定ID不因语言变化被改写。
删除的两条翻译键来自tag后新增的系统文件对话框选项，并非丢弃本tag仍在使用的译文。

宿主Qt6.12.0、SDK0.39.0取自tag依赖；插件历史SDK锁不混同宿主。包装许可及release.json动态读取宿主pin。
正式版本4.1.0+zh.1使用本仓更新列表，不误入上游APT/IFW；SemVer元数据变化不充当升级。

## tag 缺陷的最小发行修复

`pj_widgets/src/FileDialog.cpp` 在构造内嵌 `QFileDialog` 后立即设置
`DontUseNativeDialog`，再恢复有效历史和侧栏入口。Qt 6.12 在支持系统选择器的平台
先建立 native helper；如果先调用 `setHistory` / `setSidebarUrls`，这些设置会被忽略。
这是 tag 已有的初始化顺序缺陷修复，不引入后续系统文件对话框开关或文件拖放功能。
来源可核对 [Qt 6.12 的 QFileDialog 实现](https://github.com/qt/qtbase/blob/v6.12.0/src/widgets/dialogs/qfiledialog.cpp)。

候选 Windows runner 除原有全套测试，还必须通过真实 `windows` QPA 平台下既有的
4 个 `FileDialogStartFolderTest`；报告拒绝缺项、跳过和截断。默认 offscreen 的通过
不能替代这一定点检查。这些 fixture 写 Qt 自身共享设置，只在独立 CI runner 执行。

## 验收状态与发布门槛

源码初步检查可用既存Qt6.11.1工具提取目录，但不能替代最终固定Qt6.12.0检查。
最终候选必须重新执行固定工具链的源码提取、完整Linux/Windows构建、GPU与BIN等回归。
Windows安装器与ZIP在不同干净runner验收；Ubuntu22.04/24.04分别验收AppImage与DEB。
六报告、三语18截图、四原资产及hash完整才可进入视觉审阅和发布。实际结果由精确run/attempt记录，
本集成文档不是提前宣称这些任务已经通过。公开后还需重新下载校验并确认历史标签/资产未变。
