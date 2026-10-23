# PlotJuggler 4 简体中文开发说明

本开发线在官方 `main-4.x` 的真实 Git 历史上实现中文界面及 ArduPilot
DataFlash BIN 加载器。当前版本为 **`4.0.0-zh.1.rc.2`**，为第二个发布候选，不是稳定发布。
`zh-CN-4.x` 为稳定线，`zh-CN-4.x-dev` 为开发集成线；主题变更通过保留提交的
合并进入开发线，验证及发布准备完成后再晋级稳定线。初始化为空白上游基线的稳定分支
不表示已经交付汉化版本。参见[分支规范](../BRANCHING.zh-CN.md)。

## 上游与移植边界

| 项目 | 基准 |
|---|---|
| PlotJuggler 官方上游 | `PlotJuggler/PlotJuggler`，`main-4.x` |
| 精确上游提交 | `0345ec513bde7f05ad3148548ac30401f2b6f7a7` |
| 3.x 翻译参考 | 本仓库 `zh-CN` 的 `766a88d8e689c7803f32acb315ac872a0a67a57b` |
| Qt | `6.11.1`，以 `versions.env` 为准 |
| C++ / 构建 | C++20、CMake、Conan 2 |
| 插件 SDK | `plotjuggler_sdk/0.34.1`，以 `conanfile.txt` 及锁文件为准 |

4.x 是重新设计的模块化应用：界面、数据存储、脚本、插件宿主和 2D/3D 视图已分离。
3.x 的 Qt5 插件不能直接加载；旧工程配置、发布工作流及诊断补丁没有整体合并进来。
基准与来源的机器可读记录位于 [upstream-baseline.json](upstream-baseline.json)。

## 界面语言

- 新配置默认使用简体中文。首选项的“语言”可选择中文或 English，确认后在下次启动生效；取消不保存。
- `plotjuggler4 --language en_US` 或 `--language zh_CN` 只覆盖当前会话，不改写保存的选择。
- 无效的已保存语言值回退到英文源文。语言设置不修改数据解析或数值格式使用的 locale。
- 翻译目录与 Qt 标准对话框译文编译进程序，无须在运行时下载语言包。
- 英文源字符串和数据、主题、插件等序列化标识保留原值，便于合并上游更新。

当前目录覆盖应用、插件市场、插件对话框宿主、绘图、2D/3D 场景和通用控件中
**1,968 条 Qt 可提取消息**，未完成条目为 0。其中 97 条精确复用了 3.x 中文翻译。
这个数字是指定提取范围的目录覆盖率，不代表所有可见内容均已汉化。
内置 Lua 滤波器的名称、说明及参数标签仅在显示时翻译，稳定 ID、参数值、源码和生成的
曲线名称保持不变，自定义滤波器元数据不改写。启动横幅的 15 条随机文案可翻译。
中文会话尊重趣图/严肃启动图设置。现有无文字哭猫/胜利小孩底图配合 Qt 可翻译排版组成
8 组已审阅的额外中文双格趣图；这不是原 37 张的翻译。原图原梗另有 33 张可用
（31 张中文像素版本及 2 张仅含产品/技术名的原图），共组成 41 项中文池。原编号
09/11/13/24 暂不可用，未进入中文池，也不回退到英文图。英文原池不变，不能声称原 37 张全完成。
市场当前固定目录共 30 项（Windows 平台显示 29 项），未安装项目的名称、描述和分类也翻译；
保留英文搜索和 canonical ID，未知或改变的原文保守回退。
固定随包官方插件使用精确 UI 字节哈希、控件属性及固定版本的显示映射；Windows CRLF 仅在身份哈希前规范化为 LF。
5 个插件采用固定源提交的显示层补丁重建，覆盖内部文案与用户数据混排、固定导入错误等场景；Windows 使用其中 4 个，Assistant 仅随 Linux 提供。原始协议和数据保持不变。
Mosaico 1.3.0 保留官方原包与混合正文剩余英文，不重建其独立 SDK；例外及原因见 [#20](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/20)。
后装第三方插件不在固定随包范围；部分浏览器上传错误、WebAssembly、macOS 仍需单独验证；
原生候选包的独立验收入口见下文。rc.2 另外覆盖扩展安装/解压、URDF/网格错误和安装器自定义页。
发布状态与最终验收范围以对应 Release 和固定提交的 CI 记录为准；旧 rc.1/rc.2 包不变。
本段新增修复属于 rc.2 后开发线，尚不是新发布包；历史 Release 文档继续描述当时已发布字节。
Windows GUI 子系统、嵌入图标和重定向 CLI 的新检查针对实际 PE；自动化不能替代 Windows 桌面视觉验收。
更新检查只查询本仓同一主版本汉化发布列表，包含候选序号比较，不调用未配置的 IFW/APT 上游更新。
安装器标准页中文和重启式语言切换实现见 packaging/installer/README.md，实际安装验收另行记录。
同一系统用户下验证新原生候选包时，可显式使用
[`--profile-dir` 独立测试目录](ISOLATED_PROFILE.zh-CN.md)，隔离应用设置、市场仓库及核心缓存。
该选项不是插件沙箱，也不约束 IFW 安装器。

## ArduPilot BIN 插件

原始项目是 LGPLv3 的
[ArduPilot/plotjuggler-apbin-plugins](https://github.com/ArduPilot/plotjuggler-apbin-plugins)。
独立的真实 fork 位于
[reliable-ly0411/plotjuggler-apbin-plugins](https://github.com/reliable-ly0411/plotjuggler-apbin-plugins)：
`main` 跟随上游主线并保留最小同步管理文件，`plotjuggler-4.x-sdk` 保存新 SDK 适配。
同步规则、上游来源及许可证保留在插件仓库中。

本工程用 Git 子模块的**固定提交**引用 SDK 适配版本，在构建时编译独立的共享插件，
不把 LGPL 解析器静态链接到 MPL 应用，也不在运行时下载或追踪插件分支的最新内容。
当前固定提交为 `0cc7cc10a25af3cb2ab122861b9be4fc01c99da5`，插件版本为
`1.2.0-pj4.rc.1`。对应源代码及许可证随子模块保留。SDK 目前没有旧版的逐字段 tooltip setter，
原始字段说明保留在数据集元数据中；界面展示的差异见插件 `sdk4/UPSTREAM.md`。

## 构建与回归

先按[上游构建指南](../BUILDING.md)准备系统依赖与 Qt，然后初始化子模块：

```sh
git submodule update --init --recursive
./scripts/install_qt6.sh
./build.sh
```

Windows 使用上游的 `build.bat` 入口及固定的 MSVC 2022 / Qt 6.11.1 工具链。
`PJ_BUILD_ARDUPILOT_PLUGIN=OFF` 可以显式关闭原生 BIN 插件。没有初始化插件子模块且保持
默认启用时，配置会明确失败，避免生成看似完整却缺少 BIN 功能的构建。
WebAssembly 不启用这个原生共享插件。

不构建完整 SDK/渲染依赖也能运行语言专项测试：

```sh
python3 tests/test_branch_policy.py
python3 tests/test_check_translations_4x.py
python3 tests/check_translations_4x.py --lupdate .qt/6.11.1/gcc_64/bin/lupdate
cmake -S pj_app/tests/i18n -B build-i18n \
  -DCMAKE_PREFIX_PATH="$PWD/.qt/6.11.1/gcc_64"
cmake --build build-i18n
ctest --test-dir build-i18n --output-on-failure
```

完整原生构建启用 `PJ_BUILD_TESTS=ON`，会额外注册应用首选项、浏览器设置白名单、
BIN 解析及动态插件 ABI 回归。`ArduPilotFileLoaderTest` 还通过真实 `FileLoader`、
数据存储及曲线目录验证中文路径、重复导入、多个文件间的状态隔离、损坏格式回滚，
以及上游真实日志。Linux 的渲染测试需要有效的 OpenGL/X11 环境；
`ArduPilotLayoutRestoreTest` 还启动真实应用，在中英文下恢复同一中文路径日志与
曲线布局，要求实际绘图适配器提供有限样本、正确的物理范围及可见视口；
不会用重新绑定曲线、重置缓存或手动缩放掩盖首次恢复失败。
CI 使用 Xvfb 并要求 GPU 测试实际运行。Windows CI 使用相同 SDK 与 MSVC 版本。
`PreferencesLanguageTest` 还构造真实主窗口和首选项窗口，分别检查中文、英文菜单与语言控件，
并执行窗口像素抓取。CI 将这些仅含合成数据与独立测试配置的截图保存到测试报告中，
供检查文字缺字、截断和布局；自动断言通过不能替代截图的人工视觉检查。
截图用例还要求 Latin 与常用中文字形实际可用，避免只有方框的图片被误判为通过。
Windows 的 Qt offscreen 平台不读取原生系统字体数据库；CI 为测试下载固定提交及
SHA-256 校验的 Noto Sans CJK SC 2.004（SIL OFL-1.1），通过 `QT_QPA_FONTDIR`
提供字体。发布包另行暂存并校验同源字体及许可，应用启动时从包内 `bin/fonts` 注册
CJK 回退；原生产品不依赖测试专用环境变量，也不改变用户选择的字体族。

翻译更新只在显式执行下列命令时改写目录，普通构建不会修改源文件：

```sh
python3 tests/check_translations_4x.py --lupdate /path/to/lupdate --update-ts
```

检查器验证提取集合、上下文、占位符数量、复数、富文本及链接属性。
`--catalog-only` 仅检查已有目录结构，明确不验证源代码覆盖率，不能替代带 lupdate 的检查。

[Chinese 4.x development checks](../../.github/workflows/zh-4x-ci.yml)
仅构建、测试并保留测试报告，不创建 tag、Release 或生产安装包。
具体通过、失败和待验证项目应以对应提交的 CI 结果与 PR 验证记录为准。

## 已知诊断边界

3.x 的 [Issue #3](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/3)
及 [PR #6](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/pull/6) 中的 Qt5
启动图像诊断仍未解决，未作为修复移植到 Qt6 的 4.x 生产代码。
4.x 保留本代启动图像管线；专项语言测试通过不等于该历史问题已修复，也不等于所有平台
完整应用与安装包均已验收。

## 发布候选与最终包验收

发布规范见根目录 [RELEASING.md](../../RELEASING.md)。
`zh-4x-packages.yml` 在标准 Linux/Windows runner 上构建候选，保留与开发回归
相同的 SDK、Qt 和工具链约束，额外暂存固定 BIN DSO、许可及中文字体。它不写标签或 Release。
最终 IFW 安装、AppImage 原包运行及 .deb 安装在独立环境中检查实际内嵌版本、全部插件、
Python、中文文件名真实 BIN、实际曲线样本与视口及中英文截图。导入日志及绑定存在
不等于曲线可见，自动样本断言也不替代最终截图的视觉审阅。详情见
[包装验收说明](../../packaging/localization/README.md)。

候选不启用上游 APT/Windows 自动更新发布，不冒充上游正式发布。

原包干净环境验收区分插件清单与运行状态：Linux 包含 21 个插件，其中 ROS 2 订阅插件需要外部 ROS 安装及环境设置。无 ROS 的验收环境要求其给出明确的未安装诊断，其余 20 个插件仍须全部加载并匹配版本；不将该边界视为 ROS 功能通过。Windows 包含并验证 19 个插件。
