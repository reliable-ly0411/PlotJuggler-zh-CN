# PlotJuggler 简体中文与 ArduPilot 版本

本分支对应本机使用的 Qt5 PlotJuggler 3.17.2，初始基线为官方
`3.17.2` 标签（`034a5cc919909aebb124e0dc1abbe2029c3eed0f`）。
官方主项目已发布 Qt6 的 4.0.0；其插件接口与 3.x 不兼容。
这里仅同步官方 `main` 的 3.x 维护线，禁止自动跨到 4.x。

## 使用

解压 Windows portable 包后运行 `plotjuggler.exe`。安装器默认安装到
`PlotJuggler-zh-CN` 独立目录；配置也使用独立应用标识，不覆盖原版设置。
文件名和安装路径均不要求使用中文。

默认使用简体中文。通过“帮助 → 语言 → English”切换并重启，或直接运行：

```text
plotjuggler.exe --language en_US
plotjuggler.exe --language zh_CN
```

版本号采用 `3.18.0-zh.1+upstream.3.17.2.apbin.1.g<提交号>` 形式：3.18.0 是兼容新增功能的 fork 次版本，zh.1 是首个汉化先行版，
加号后的信息标明官方基线、解析修订和源码提交，符合 SemVer 2.0.0。
构建信息不参与版本优先级比较；已发布标签和包不得覆盖，后续功能或修复必须递增适当版本。
Qt Installer Framework 内部组件版本采用数字先行版 3.18.0-1；程序和文件名显示完整 SemVer。包内 `BUILD-INFO.json` 记录准确源码提交和解析器版本。

## ArduPilot 解析范围

默认构建并随包提供独立共享插件 `DataAPBin`。启动时沿用 PlotJuggler 的
插件自动发现机制，第一次打开 `.BIN` 文件时无需手动安装插件。
该功能并非自动连接飞控，也不是 MAVLink 遥测解析器。

解析源码来自 [ArduPilot 官方插件](https://github.com/ArduPilot/plotjuggler-apbin-plugins)，
固定提交 `3e2f9253adc2d41e17b2f0fec74f4b2487c42fb0`，保留原作者信息和 LGPL-3.0。
应用本身保留 MPL-2.0；插件仍单独动态链接，源码位于
`plotjuggler_plugins/DataLoadAPBin`，许可证随二进制一并提供。

- 支持 DataFlash 二进制 BIN 的 FMT、FMTU、UNIT、MULT、TimeUS 和字节实例标记。
- TimeUS 统一转换为秒；有有效 GNSS 时间信息时沿用官方插件的时间同步逻辑。
- 默认显示单位，按 FMTU/MULT 应用倍率。没有单位/倍率元数据的旧日志保留原始数值。
- 保留官方参数、状态文本和消息说明功能；增加重复加载时的完整状态清理、
  FMT 长度检查以及 128～255 实例编号的处理。
- 不支持 DataFlash 文本 `.log`、仅有 TimeMS 的旧记录，以及 ISBH/ISBD
  批量惯性数组波形。字符串/数组字段不会伪装成数值曲线。
- 64 位整数作为 double 曲线显示，超过 52 个有效二进制位可能损失精度。

可以关闭此插件，其他格式的加载器保留：

```text
Windows: plotjuggler.exe --disabled_plugins DataAPBin
Linux:   plotjuggler --disabled_plugins libDataAPBin
```

源码构建时使用 `-DPJ_BUILD_ARDUPILOT=OFF` 可完全排除它。
单位标签是序列名称的一部分；与不带单位的旧插件布局互换时需重新绑定曲线。

## 翻译维护与已知边界

Qt `.ts` 为唯一翻译来源，构建时通过 Linguist 编译并嵌入 `.qm`。
当前覆盖主菜单、对话框、设置、常用插件、错误提示和帮助内容。
技术标识、快捷键、协议名、格式表达式和用户数据保持原样。

第三方运行时异常文本、用户消息内容、ArduPilot XML 字段说明、插件返回的
动态名称以及诊断标准输出可能仍为英文。这些内容不会被盲目替换。
Qt 标准对话框优先使用随包或系统 Qt 的 `qtbase_zh_CN` 翻译。

```text
lupdate plotjuggler_app plotjuggler_base plotjuggler_plugins -no-obsolete -ts plotjuggler_app/translations/plotjuggler_zh_CN.ts
python tests/check_translations.py --fresh
```

`--fresh` 重新提取到临时文件，新增未翻译消息和丢失的 `%1` 等占位符会令检查失败。
本分支不发送机器标识或使用遥测。

## 同步和自动构建

`zh-sync.yml` 每日 03:23 UTC 以及手动触发。它将官方 `main` 合并到 `zh-CN`，
保留定制提交，不使用强推、重置或自动选择冲突一方。
冲突、版本跨代或翻译校验失败时，取消本次合并，保留远端定制分支，
Actions 标红并上传 JSON 报告及冲突文件列表。没有上游变化时成功返回 `up_to_date`。
推送竞争通过普通 Git push 拒绝处理，需查看报告后重试。

同步任务只使用仓库临时 `GITHUB_TOKEN` 的 `contents:write`。构建任务仅需
`contents:read`，不使用 PAT，不向第三方授予权限，不运行外部 PR 的特权脚本。
官方其他工作流保留在源码中，但仅在官方仓库运行。

`zh-windows.yml` 构建 Windows x64 安装器和 portable 包；`zh-linux.yml` 构建
Linux x86_64 AppImage。两者复用上游 Qt5 构建/打包方法，使用 GitHub 公共 runner。
普通提交和 PR 自动构建；同步提交通过可复用工作流显式构建，避免依赖
GITHUB_TOKEN 推送无法再次触发工作流的行为。

构建成功还必须通过合成 DataFlash 测试、翻译检查和中英文真实窗口截图验收，
之后才上传包和证据。工作流配置已提交不等于构建成功；以对应 Actions 运行结果为准。

## 本地构建和验收

沿用上游 CMake/Qt5 工具链，额外需要 Qt LinguistTools 与 Python3。
ArduPilot 测试默认开启，可用 `-DPJ_BUILD_ARDUPILOT_TESTS=OFF` 关闭。

```text
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
python tests/test_sync_upstream.py
```

测试日志均为合成数据，不包含飞行记录、位置、硬件信息或用户文件。
Git 同步保护测试使用一次性临时仓库，不接触用户的其他仓库。
