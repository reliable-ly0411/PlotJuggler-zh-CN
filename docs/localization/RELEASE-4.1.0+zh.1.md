# PlotJuggler 4.1.0+zh.1 · 简体中文 / 繁體中文 + ArduPilot BIN

本版基于上游正式 `4.1.0` 标签，应用基线锁定为
`1b8fb491f56cc185ae395e2c7a0561443ad18d07`，不跟随继续前进的 `main-4.x`。
这是非官方汉化发行，不是未经修改的官方二进制。通过本页所列最终原包验收后发布为正式版并设为 Latest；旧标签及原包保持不变。

## 上游 4.1.0 发布说明（全文）

来源：[PlotJuggler/PlotJuggler 4.1.0](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.1.0)。
以下完整保留对应上游 Release 正文，其中上游的 Web、APT、Windows 自动更新、conda、Nix 和 macOS 介绍不等于本汉化发行提供这些渠道或已经验收。

# PlotJuggler 4.1.0

PlotJuggler 4.1 is a large release. It covers 171 commits since 4.0.0. The main changes:

- **Native GPU rendering everywhere.** Plots, the 3D scene and the media viewer now render through Qt's RHI. They use Direct3D 11 on Windows, Metal on macOS, OpenGL/Vulkan on Linux and WebGL2 in the browser.
- **Derived objects and Custom Topics.** Luau and Python scripts can now produce point clouds, 3D scene entities, image annotations, voxel grids and plottable series from recorded objects. All of this is managed in the new **Custom Topics** panel.
- **Custom Widget panels.** Docks whose content is a Qt widget provided by a Widget plugin.
- **PlotJuggler in the browser** at **[app.plotjuggler.io](https://app.plotjuggler.io)**, with ready-to-open sample datasets.
- **New ways to install:** a conda package for RoboStack users, a Nix flake, a portable Windows ZIP, an apt repository and Windows auto-update.
- **Qt 6.12 LTS**, plus many correctness and performance fixes in the data store (large-file import is up to ~3x faster).

---

## ✨ New features

### Rendering
- **QRhi renderer for every GPU view.** The Scene3D view, the plot canvas and the media viewer use the platform's native graphics API:
  - Direct3D 11 on Windows, with Qt falling back to WARP.
  - Metal on macOS, with a probe that falls back to OpenGL.
  - OpenGL on Linux and WebGL2 in the browser.

  `PJ_GRAPHICS_API` overrides the choice at run time for diagnostics. The plot canvas is faster than the previous OpenGL canvas on large static, streaming and zoom/pan workloads. If its GPU pipelines cannot be created, it falls back to the raster canvas.

### Derived objects, scripting and Custom Topics
- **Custom Topics panel** (replaces "Custom Series"):
  - It lists transform outputs, the object outputs of on-demand recipes and the number columns of scripted series.
  - Each row shows its owner's badge and its compute state (computing, lag, errors, findings).
  - A series replaying over a recording shows a cancellable progress bar. Stopping keeps the rows already computed.
  - Deleting a recipe is an undoable step. A recipe owned by another plugin, or one that other recipes depend on, is protected.
  - "+" and the pencil open the editor extension that declares the `custom_topics_editor` capability (for example the Transform Editor).
- **On-demand recipes.** Scripts run off the GUI thread on a worker pool and are evaluated at the cursor, at the live edge while streaming, or over a window or instant. Results are cached and computed upstream first along the recipe graph. A result that becomes stale keeps showing the previous one until the new one is ready.
- **Inputs** can be point clouds, images, depth, video frames, string and number series, and TF.
- **Script outputs:**
  - `pj.scene`: spheres, cubes, text and line strips.
  - `pj.annotations`: points, circles and text over images.
  - `pj.cloud`: point clouds with xyz, xyzi and xyzrgb presets.
  - VoxelGrid builders and voxel downsampling.
  - Image and depth operations.
  - Plottable number series.
- **Luau and Python** are both supported. Python runs in an embedded interpreter with a strict sandbox profile, memory caps and a watchdog. Each run gets a fresh namespace, and a script is compiled once.
- **Series compute the visible range first,** then backfill the rest of the recording. Plots say when a series is not computed yet.
- **Scene layers on derived topics** explain why they are empty (missing input, error), show the compute lag and frame findings.
- **Marker rules run off the GUI thread.**
  - An "Automatic" reload brake coalesces input changes.
  - Plots show a "Computing markers…" / "Marker rule failed" note while the markers stay drawn.
  - A cancelled run stops its script.
  - Marker topics are recognised by their metadata instead of their names.
- **Layouts** save and restore on-demand recipes. Recipes that did not change stay live across an undo or a layout reload instead of being recomputed.

### Plugins and extensions
- **Custom Widget panels:** a dock that hosts a Qt widget created by a Widget plugin.
  - The panel wires series to the widget's named inputs and pushes values at the tracker time.
  - The panel is saved in the layout.
  - If the plugin is missing or fails, the panel shows a placeholder with the reason and keeps the layout entry.
- **Plugins can embed live 2D/3D scene views** in their dialogs and panels.
- **Plugins can create their own 3D/2D tabs,** attach object topics to them and focus them.
- **Catalog snapshot v2** gives plugins every object, derived and marker topic, with its metadata and time range.
- **Feature catalog service** (`pj.feature_catalog.v1`) tells a plugin what this PlotJuggler build and its installed extensions offer.
- **Drag and drop onto plugin panels:**
  - Object topics drop by name, or as `source:topic` when two datasets share the name.
  - The drop says which data source it came from.
  - `CameraInfo` rows can be dragged to plugin panels.
- **Plugin file pickers** open at the folder and file name the plugin suggests ([PlotJuggler#1453](https://github.com/PlotJuggler/PlotJuggler/issues/1453)).
- **Plugin chart previews** (Anomaly Detector, FFT, Transform Editor) pan live, and wheel zoom-out stops at the data extent.
- SDK moved to **plotjuggler_sdk 0.39.0**.

### Scene 2D / 3D
- **Scene2D:**
  - Dropping a full-frame image, depth or video onto a dock **replaces the background** instead of stacking another one. Overlays keep stacking.
  - **View rotation** of 0°, 90°, −90° or 180°, saved in the layout. Text labels stay upright.
  - Zoom and pan keep the image point under the cursor when the image is letterboxed.
- **Scene3D:**
  - Robot meshes loaded over http(s) also fetch their textures.
  - Cloudini V4–V6 point clouds decode (Cloudini 1.4.1).
- **TF:**
  - Each sample keeps both its header stamp and its log time, so objects are placed with the transform of their own instant.
  - Identical republished transforms are no longer stored.
- **Mixed-dataset layouts.** A layout whose scene saved topics from two datasets now binds to the first saved dataset, whatever the load order. The other dataset's elements are refused visibly.

### Application
- **File → Open Data File...** (Ctrl+O).
- **System title bar by default.** The custom frameless look is now an option: Preferences → Appearance → "Frameless window". On Windows and macOS the title bar follows the app's light/dark theme.
- **Command line:** repeatable `-d/--datafile` options and positional file paths. The files finish loading before an optional layout (`-l`), and they replace the sources saved in that layout.
- **Update check** asks the install's own channel:
  - Debian package: `apt-cache policy`.
  - Windows installer: the maintenance tool, with an "Update now" link.
  - Other installs: GitHub releases.
- **X/Y wheel zoom:** holding X or Y while scrolling over the focused plot zooms only that axis.
- **State Transitions** accepts float columns that only ever held whole numbers (for example JSON integers parsed as double).
- **Linked time ranges** are kept when a new plot is added ([PlotJuggler#1437](https://github.com/PlotJuggler/PlotJuggler/pull/1437)).
- **Diagnostics:** file-loader failures and plugin warnings now reach the diagnostics bell and `--dump-diagnostics`.
- **Streaming:** a derived node that falls behind the retention window skips to the live edge and records the gap.

### PlotJuggler in the browser (WebAssembly)
- **Hosted at [app.plotjuggler.io](https://app.plotjuggler.io).**
- **Welcome dialog with samples:**
  - Built-in filters on a Nissan Leaf drive.
  - A Franka FR3 arm.
  - ANYmal walking the GrandTour forest trail (cameras, lidar, robot model).
  - A Boreas self-driving city drive (camera, 128-beam lidar, car model).
  - "Upload your own…".
- **Deep links and hosted layouts:**
  - `?preset=<id>` opens a sample directly; its recordings are fetched while the app boots and kept in the browser cache for later visits.
  - Layouts can be opened by URL.
  - A robot can serve the app next to `plotjuggler_bridge` and stream live with no setup dialog.
- **Feature parity with the desktop:**
  - Video playback (FFmpeg/dav1d), Scene2D, Scene3D and on-demand Python scripts.
  - Firefox support.
- **Loading:**
  - PlotJuggler's own loading page with real download progress, and a warning before downloading on phones.
  - A clear message when the browser cannot isolate the page.
- **Memory:** about 52% lower (the 261 MB Boreas sample: wasm heap 1084 → 443 MiB).

### Packaging and distribution
- **conda package for RoboStack users** (Jazzy, Kilted), on the prefix.dev `plotjuggler` channel.
- **Nix flake** (community-maintained) for a native Linux build ([PlotJuggler#1423](https://github.com/PlotJuggler/PlotJuggler/pull/1423), thanks @mevatron).
- **Portable Windows ZIP** next to the installer.
- **apt repository and Windows auto-update channel.**
- Documentation for direct builds, offline dependency preparation and migration ([PlotJuggler#1442](https://github.com/PlotJuggler/PlotJuggler/pull/1442)).

---

## ⚡ Performance
- **Faster import.** Large files load up to ~3x faster after a hash-collision fix on the append hot path. A 1.07 GB PX4 ULog drops from 79 s to 37 s, or from 62 s to 21 s with bound appends.
- **Smaller float columns.** Float columns that only hold whole numbers are stored frame-of-reference encoded.
- **Marker rules** copy their input series in linear time instead of quadratic: a 50k-sample series takes milliseconds instead of ~7 s.
- **Luau scripts** reuse one sandboxed state per thread, about 7x faster per run. A 36k-row series replay goes from 1.09 s to 0.40 s.
- **Retention eviction** is linear; Python list views are reused; video frames convert to RGB faster.
- **Scene3D:**
  - Point-cloud uploads no longer copy the batch.
  - Markers are cached per layer.
  - 10M-point clouds render at parity with the previous renderer.
- **Browser:** downloads are hashed with a single WebCrypto digest (Boreas sample 7.8 → 6.7 s to data).

---

## 🐛 Bug fixes
- **Plots stayed empty after a dataset reload or replace** ([PlotJuggler#1456](https://github.com/PlotJuggler/PlotJuggler/issues/1456)).
- **A record was dropped when a field changed type** (e.g. a JSON integer becoming 1.5). Values are now converted when the conversion is exact. Otherwise only that field is null, and the rest of the record is kept ([PlotJuggler#1427](https://github.com/PlotJuggler/PlotJuggler/issues/1427)).
- **File dialogs froze for over a minute** when the start folder was on an unreachable network drive. They now fall back to the home folder after 2 s ([PlotJuggler#1446](https://github.com/PlotJuggler/PlotJuggler/issues/1446)).
- **Moved or copied layouts:** a layout folder moved or copied together with its data now keeps its data, scenes and robot model.
- **Generic layouts:**
  - Marker generators follow their dataset when a layout moves.
  - A generic marker rule with no inputs binds.
  - On-demand recipes restore when the layout is opened on another recording.
- **Recipe chains:** chaining recipes in the Transform Editor no longer fails with "unknown input" when an input is dataset-qualified.
- **Crashes on quit:**
  - While a video was playing in Scene2D.
  - With Scene2D video docks open (docks are now destroyed before plugins unload).
  - From the Marketplace window outliving its manager.
- **XY curves:** creating an XY curve from a previewed topic crashed ([PlotJuggler#1433](https://github.com/PlotJuggler/PlotJuggler/pull/1433)).
- **Playback:**
  - The step control stopped working after the range changed ([PlotJuggler#1443](https://github.com/PlotJuggler/PlotJuggler/pull/1443)).
  - Playback controls and scene settings give clearer feedback.
  - Deferred depth drops are validated.
- **Plot behaviour:**
  - A plot fitted before it had data now frames its rows once data arrives.
  - The topic streaming menu no longer gets in the way of right-dragging two selected series to make an XY plot.
- **Scene2D:**
  - A restored dock with no other GPU view in the window showed a black view.
  - Odd-sized 4:2:0 video (e.g. AV1) had shifted chroma, on both the CPU and GPU paths.
  - Hardware-decoded video lost its colour tags, and full-range video lost its range.
  - A vertically panned image was clipped incorrectly.
- **Data store:**
  - Null handling in constant-encoded chunks.
  - Precision above 2^53.
  - Partial Arrow batches.
  - Locking in dataset merges.
  - Retention floors.
  - Several ObjectStore lifetime issues (a double free on a rejected lazy push, destruction under locks, merges of mismatched payload encodings).
- **Derived transforms** skip null input cells instead of treating them as 0 or "".
- **Python:** a failed Python startup stays failed, reports its cause and frees the interpreter lock.

---

## 🔧 Internal changes and refactoring
- **Toolchain:**
  - **Qt 6.12.0 LTS** and **Emscripten 5.0.5**.
  - One Qt pin shared by the desktop and browser builds.
  - Qwt is built from source everywhere.
- **Dependencies:** plotjuggler_sdk 0.34.1 → **0.39.0**, Cloudini 1.4.1, refreshed `conan.lock`.
- **Renderer:**
  - The legacy OpenGL Scene3D renderer and the separate browser layer/dock forks (~12k lines) are deleted.
  - One layer set, and one pass per layer family, behind a single contract.
  - Shader packs are baked for every backend and hash-checked at configure time.
- **New `pj_tf` module:** a Qt-free TF library. `TransformService` moved to `pj_runtime`, and TF snapshots are immutable (copy on write).
- **Engines** are named by their trigger: `DerivedEngine` → `IncrementalEngine` and `MarkerService` → `BatchEngine`. The new on-demand stack:
  - `EnginePool`, a worker pool plus a Python lane.
  - `RecipeGraph`, `ResultHistory`, `InputStager`, `NodeScheduler`, `OnDemandService`, `GridRunner` and `SeriesRunner`.
  - The ObjectStore gains atomic multi-topic bundles.
- **Persistence:** derived-recipe persistence moved out of `MainWindow` into `DerivedObjects`.
- **One embedded Python interpreter,** with cooperative limits, shared by filters and on-demand scripts.
- **Browser code:**
  - One size-capped fetch (`fetchBytesWithLimit`) and a streaming `BrowserFetch` that works around a Qt WebAssembly network leak.
  - One HTTP contract shared by the dev server and the Cloudflare Worker.
- **Browser licensing:** the bundle is distributed under GPL-3.0 (it statically links Qt's WebAssembly plugin). Licences are listed in About, and a source offer ships with each deployment. The desktop app stays MPL-2.0.
- **Build:**
  - `build.sh` caps parallel jobs by available memory (`PJ_BUILD_JOBS` overrides).
  - It links with mold when installed.
  - A pre-commit rule rejects `near`/`far` identifiers, which `windows.h` defines as macros.
- **Tests and CI:**
  - `PJ_REQUIRE_GPU_TESTS=1` makes GPU-availability skips fail on CI.
  - Point-cloud golden images run in CI.
  - Several flaky tests fixed.
  - The Pixi, WASM, Sanitizers and macOS lanes run nightly, only when main moved.
  - Faster macOS, Linux and WASM lanes.
- **Docs:**
  - Slimmer agent-facing `CLAUDE.md` files.
  - New `ARCHITECTURE.md` files for `pj_app`, `pj_runtime` and `pj_plotting`.
  - The derived-objects design docs turned into a maintenance reference.

---

**Contributors:** @facontidavide, @Alvvalencia, @mevatron (first contribution 🎉)

**Full Changelog**: https://github.com/PlotJuggler/PlotJuggler/compare/4.0.0...4.1.0

## 汉化与插件差异

- 提供简体中文、繁體中文（台灣）和 English，默认简体中文。语言切换在下次启动生效，命令行 `--language` 只影响当前会话。数值和数据解析 locale 不变。
- 简繁目录各覆盖 2,091 条 Qt 可提取消息，未完成 0。目录覆盖率不代表所有第三方插件、像素图片或平台界面均已翻译。
- 保留中文文件对话框、固定市场目录显示映射、内置滤波器显示翻译、中文趣图、独立 profile 及安全外部链接处理。英文源字符串、数据标识和保存语义保留。
- 新增已安装插件详情的作者、许可证、网站与源码信息，以及固定官方 FFT 1.0.1 的显示映射。保留 CSV Loader 1.0.7 的 UTF-8 路径预览/导入修复。
- ArduPilot DataFlash BIN 作为独立 LGPL-3.0-only 共享插件分发，版本 `@BIN_VERSION@`、提交 `@BIN_SHA@`。不静态嵌入 MPL 应用；来源及许可证随包保留。
- 固定官方 registry 为 `2696403e106c6960541b8da19987ece35a24597e`。Windows 包含 18 个官方插件和 BIN；Linux 包含 20 个官方插件和 BIN。ROS 2 订阅插件需要用户另装并配置 ROS 2。
- 本版汉化重建集合共 6 个，Windows 使用其中 5 个，Linux 使用全部 6 个：`mcap-loader`、`protobuf-parser`、`toolbox-transform-editor`、`webrtc-client`、`toolbox-assistant-agent`、`csv-loader`。Assistant 仅 Linux 提供，CSV 为路径补丁，其余保留显示补丁。各插件使用自己的固定源码、历史 SDK 和许可证，不用宿主 SDK 改写插件来源。
- 修复 Qt 6.12 在 Windows 等支持系统选择器的平台忽略文件对话框历史/侧栏恢复的初始化顺序问题，不加入开发线的系统文件对话框切换或文件拖放功能。
- 保留本分支原有 Windows GUI 子系统、应用图标和可重定向 CLI 发行契约，沿用版本资源及 core-only console 修复。这部分发行补丁与纯上游标签的差异明确记录，不宣称二进制与上游完全相同。

本发布分支从已审阅的开发历史保留翻译和插件修复，对上游 tag 后的 14 个提交逐项审查，排除其应用功能增量，并保留上文明确说明的 Windows 发行契约及最小 tag 缺陷修复。
开发线中的文件拖放、系统文件对话框开关、Wayland 包装、macOS 中文包装以及较晚通用修复不因已进入开发线而自动进入本版。
开发分支本身保持原有功能与 Git 历史，未被回退。详见
[标签集成记录](../../blob/@SOURCE_SHA@/docs/localization/RELEASE-4.1.0-INTEGRATION.md)。

## 下载、安装与升级

- Windows x64 离线安装器：`PlotJuggler-4.1.0+zh.1-Windows-x64-zh-CN.exe`。
- Windows x64 免安装包：`PlotJuggler-4.1.0+zh.1-Windows-x64-portable-zh-CN.zip`。
  解压完整目录后运行 `bin/PlotJuggler4.exe`。免安装不表示默认配置完全便携，可用 `--profile-dir` 指定独立绝对路径。
- Linux x86_64：`PlotJuggler-4.1.0+zh.1-x86_64-zh-CN.AppImage`。赋予执行权限后运行；无 FUSE 时可设置 `APPIMAGE_EXTRACT_AND_RUN=1`。
- Ubuntu amd64：`plotjuggler4_4.1.0+zh.1-1_amd64-zh-CN.deb`。以 `sudo apt install ./文件名.deb` 安装，然后运行 `plotjuggler4`。实际验收 Ubuntu 22.04 与 24.04，不扩大为全部 Debian 衍生版本。
- 先校验同页 `SHA256SUMS.txt`。包内包含相应 Qt、Python、字体和许可。GitHub 自动 Source code ZIP/TAR 不包含子模块，源码构建须递归初始化固定子模块。

从旧 rc.4 升级请直接下载本页的新包。旧二进制的更新检测不能识别新的 `+zh.1` 正式标签形状，旧附件不会被修改以补此行为。
新版本的更新检查始终查询本仓、同主版本的汉化 Release，并提供手动下载，不跳向官方 APT 或 IFW 更新源；正式安装不会推荐候选版本。

升级前保存布局和配置备份，先用新的 `--profile-dir` 验证。此选项不是插件沙箱，也不约束安装器；
恢复标记与 Qt 文件选择器的共享状态例外见下文。
未知用户替换插件和后装市场版本按既有来源策略保留；市场再次安装官方包可能覆盖汉化或 CSV 路径修复。
回退应退出应用后正常卸载/选择保留旧包，并恢复备份，不假设不同版本的布局和设置完全兼容。

版本映射：应用 `4.1.0+zh.1`、tag `v4.1.0+zh.1`，Debian `4.1.0+zh.1-1`，IFW `4.1.0.1.1.0`。
`+zh.1` 是不参与 SemVer 优先级的构建元数据；后续正式修复必须递增真实版本，不能只把元数据改为 `+zh.2` 冒充升级。

## 构建、最终原包验收与溯源

源码提交 `@SOURCE_SHA@`，源码树 `@SOURCE_TREE@`。
候选构建和最终验收：[GitHub Actions @RUN_ID@](@RUN_URL@)。
工作流 SHA、源码 SHA、树、run 和 attempt 必须一致；验收完成后提升同一原包，不暗中重建。

- 宿主 Qt 6.12.0、PlotJuggler SDK 0.39.0、C++20，Windows MSVC 194。固定重建插件分别使用自己的 SDK 0.20.0、0.32.0 或 0.34.1，来源保持独立。
- 两平台完整应用和独立语言/BIN回归；GPU 测试必须执行，不以跳过当通过。
- 六次最终包验收：Windows 安装器与免安装包各一次，Ubuntu 22.04/24.04 的 AppImage 与 DEB 各一次。
- 每组检查版本与来源、实际 DSO、Python、中文路径公共 BIN 的 1,940 条数值序列、CSV ASCII/中文路径、曲线有限采样及非默认可见视口；三种语言共 18 张最终截图供文字、字形、截断和曲线审阅。
- Windows 19 个插件均要求加载。Linux 校验 21 个插件的包内清单，实际加载其中 20 个；ROS 2 缺失外部环境的精确诊断作为明确未验证项，不放行其他插件失败。
- 原始包 hash 在验收前后保持一致。上传草稿后及公开后分别重新下载，核对名称、字节数和 SHA-256，并验证旧标签及附件未变。
- 本文的门槛描述不代替实际结果。精确测试数量、报告、截图及构建来源以本次成功运行工件和包内 `release.json` 为准，不借用 rc.4 或开发源码结果。

## 兼容性与已知限制

- 无本汉化发行的 macOS、ARM、WebAssembly、APT、conda 或 IFW 在线更新渠道，不将上游正文中的渠道误报为本分支交付。
- Windows 包未签名，最终自动化环境为 Windows Server 2022 x64；截图与断言不代表全部 Windows 10/11 桌面、Explorer 和安装页逐项人工验收。
- Windows 可见桌面补充观察仅对应旧候选 r2：源码 `c6cb43a32291c98e65b12035c3501d6b4842ac78`，
  [构建 run 42448805739](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/42448805739)。
  已通过不带 `--language` 的真实重启，观察到首选项保存后的简中→繁中→英文→简中切换；
  简中打开 CSV，以及公开 BIN 的 `RCOU/C1` 全波形、缩放和复位均已观察到。
  截图在可见会话中查看，未保存为持久截图文件；这些操作不代表全部界面和曲线操作均已验收。
  同一旧候选的三语 CSV／BIN、19 个插件及 Python CLI 检查通过，不能替代 GUI 验收。
  这些旧候选观察不转作本页最终源码与 run 的验收结果，最终原包证据仍须按上文的精确来源单独核验。
- `--profile-dir` 仍有两项已知例外：自定义组件恢复标记使用默认 `AppLocalDataLocation`，
  启动时可能读取并尝试删除已结束 PID 的标记；Qt 文件选择器会读写用户级共享 `QtProject` 设置。
  默认应用及宿主插件设置的 INI 隔离仍有效，详见
  [独立测试目录的隔离边界](../../blob/@SOURCE_SHA@/docs/localization/ISOLATED_PROFILE.zh-CN.md#已知隔离例外)。
  旧候选的早期测试未保存共享状态基线，无法确认当时是否有标记或发生删除，也无法确认 `QtProject` 设置是否变化；
  没有发现实际删除或数据损失的证据，不能据此认定共享状态未变。
- Linux glibc 最低 2.35，原生包装使用 X11/xcb；Wayland 桌面需要 XWayland。本版不包含 tag 后新增的原生 Wayland 包装。
- Qt5/PJ3 插件不兼容 Qt6/PJ4。Mosaico 1.3.0 明确保留官方原始二进制及部分混合英文，详见 [#20](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/20)。
- 繁中非母语逐条人工审校、全部第三方插件、ROS 2 外部运行和所有图形驱动组合不在本次验收范围。原 37 张趣图中 4 张仍未进入中文池。
- 测试仅使用完全合成数据和公开上游 fixture，无私人飞控日志。fixture 的截断尾记录警告如实保留。

## 原包校验

@ASSET_TABLE@
