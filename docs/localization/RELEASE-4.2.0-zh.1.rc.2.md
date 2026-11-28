# PlotJuggler 4.2.0-zh.1.rc.2 · 中文预发布

本版基于官方 [PlotJuggler 4.2.0](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.2.0) 标签对应的 [`bca28a7a`](https://github.com/PlotJuggler/PlotJuggler/commit/bca28a7aadca75beed138bb3c2cc27184a65fea4)，保留汉化与打包改动，不带上游标签之后的开发提交。这是非官方中文预发布，不替换 Latest。

官方 4.2.0 增加了 MCP 接入、内置日志面板、文字类型派生序列和多数据集布局。完整改动及上游支持范围见[官方发布说明](https://github.com/PlotJuggler/PlotJuggler/releases/tag/4.2.0)。

- 中文候选源码：`@SOURCE_SHA@`；文件树：`@SOURCE_TREE@`
- 原始包构建及验收：[GitHub Actions @RUN_ID@](@RUN_URL@)

## 较 RC1 的改动

- 修订中文界面的译文和术语，改善实际页面上的可读性。上游仍为官方 4.2.0 发布基线。
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
