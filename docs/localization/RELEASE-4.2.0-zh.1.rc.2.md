# PlotJuggler 4.2.0-zh.1.rc.2 · 中文预发布

本版基于官方 [PlotJuggler 4.2.0](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.2.0) 标签对应的 [`bca28a7a`](https://github.com/PlotJuggler/PlotJuggler/commit/bca28a7aadca75beed138bb3c2cc27184a65fea4)，保留汉化与打包改动，不带上游标签之后的开发提交。这是非官方中文预发布，不替换 Latest。

官方 4.2.0 增加了 MCP 接入、内置日志面板、文字类型派生序列和多数据集布局。完整改动及上游支持范围见[官方发布说明](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.2.0)。

- 中文候选源码：`@SOURCE_SHA@`；文件树：`@SOURCE_TREE@`
- 原始包构建及验收：[GitHub Actions @RUN_ID@](@RUN_URL@)

## 较 RC1 的改动

- 补译 7 个随包插件的名称和说明：BLF、candump、InfluxDB 行协议、MF4/MDF、NavMap、异常检测及 CSV/Parquet 导出。
- 补译异常检测与 CSV/Parquet 导出两个面板的控件及状态提示；只匹配已知版本和原文，不改插件功能或用户数据。
- 让随包的 ArduPilot DataFlash BIN 插件 `1.3.0-pj4.rc.1` 使用同一组已核对的中文说明与错误提示；其他未知版本不套用这些译文。
- 扩展市场及首选项把插件来源称为「扩展清单」，不再使用容易与 Windows 混淆的「注册表」。
- 改写 Windows 简体中文安装器的目录警告，明确卸载会删除整个安装目录；组件选择页也明确取消勾选的后果。
- 修正繁体中文图表的缩放操作名称，区分水平缩放至完整范围与垂直缩放至可见数据范围。
- 原包的构建与验收见上方记录。旧标签及旧安装包保持不变。

## 中文发行内容

- 主程序提供简体中文、繁體中文（台灣）和 English。新配置默认简体中文；修改首选项后重启生效，不改变日志解析或数值规则。
- 原生包附带独立的 ArduPilot DataFlash BIN 插件，插件版本 `@BIN_VERSION@`，固定源码 `@BIN_SHA@`。可加载 DataFlash `.BIN` 日志并在图表中查看数值序列。
- 上游 4.x 功能和第三方插件各有独立兼容范围；不保证旧 3.x 布局或插件可直接使用。Linux 的 ROS 2 外部环境、实体 GPU/特殊缩放组合不由常规候选安装测试覆盖。

## 下载和安装

- **Windows x64**：离线安装器未签名，或将便携 ZIP 完整解压到独立目录。
- **Linux x86_64 / amd64**：本次候选目标为 Ubuntu 22.04 和 24.04。AppImage 赋予执行权限后打开；DEB 可用 `sudo apt install ./<下载文件名>.deb` 安装，运行 `plotjuggler4`。
- 试用前备份布局、配置和插件。包可用性以对应格式的 GitHub Actions 原包验收为准；不提供本版本的 macOS、ARM、WASM 或自动更新渠道。请勿将上游渠道说明视为本中文预发布的支持范围。

## 安装包与校验

@ASSET_TABLE@

下载后可用同页 `SHA256SUMS.txt` 核对。GitHub 自动生成的源码 ZIP/TAR 不含递归子模块。
