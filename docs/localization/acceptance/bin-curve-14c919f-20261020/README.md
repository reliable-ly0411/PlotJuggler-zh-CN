# PlotJuggler 4.x：首次恢复 BIN 曲线修复后的最终包证据

状态：自动验收与最终截图复核完成，原包已作为预发布公开；公开文件名校验问题已追加修正并匿名下载验证。详见 [最终发布记录](PUBLICATION.md)。本证据分支不修改已验候选源码。

## 固定身份

- 版本：`4.0.0-zh.1.rc.1`，发布标签 `v4.0.0-zh.1.rc.1`，仅预发布，不设为 Latest。
- 候选源码与 workflow SHA：`14c919f903936130c151818dbf1a0144ea6a6050`。
- 候选源码树：`b35df58b136a50c19026bd2cd866bcf8c082f866`。
- [最终候选构建与干净安装验收](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/39390859457)，run `39390859457`，attempt `1`，全部任务成功，包括 release-manifest。
- [PR 原生测试](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/39390865054)：Linux / Windows 成功。
- [PR #8](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/pull/8)。ArduPilot BIN 插件固定为 `v1.2.0-pj4.rc.1` / `0cc7cc10a25af3cb2ab122861b9be4fc01c99da5`，不是旧 PR 描述中的 v2.0.0-rc.1。

## 实际修复及数据门禁

旧包存在“导入了 1,940 个序列，但初次绑定曲线为空，移除再加才出现”的问题。修复在终止时提交尾部采样后，向已经绑定的适配器发布 `samplesIngested`；同时覆盖 fanout、无进度通知、无 ingest token、重入关闭和立即复用。回归先将同一个 Qwt 曲线绑定至已登记但仍为空的 topic，预热空缓存，再确认无需重绑即可看到采样和有效边界。

新增只读 PlotStateDump 直接观察已经附着的 Qwt 曲线适配器，不使缓存失效、不重绑、不缩放。真实 BIN、含中文路径的布局在中英文两种模式下恢复，所有五份最终安装验收及其十份状态均显示：

- topic `/RCOU`，field `C1\t[us]`；曲线可见。
- `sample_count = finite_sample_count = finite_samples_in_view = 1318`。
- x 范围 `28.416489–81.095877` 秒；y 范围 `1000–1442` 微秒。
- 视窗完全包含上述采样，y 视窗 `988.95–1453.05`，不是默认空图坐标。
- 真实日志 SHA256：`28dcbac522ceb75eee10f6af37b0d6e342c1dc79e2be1a9f766fe18a14336766`。

## 最终安装包截图与机器记录

以下均为同一次候选流程产生的**原始 PNG**，没有修改或重绘；五份 acceptance.json 和十份 PNG 均逐文件复核通过 [release-manifest.json](release-manifest.json) 的 SHA256。十份 plot-state JSON 原样保留在对应目录中。

| 最终包环境 | 中文截图 | 英文截图 | 安装验收 | 曲线状态 |
|---|---|---|---|---|
| Windows x64 IFW | [中文](reports/zh4-final-Windows/runtime/gui-zh_CN.png) | [English](reports/zh4-final-Windows/runtime/gui-en_US.png) | [JSON](reports/zh4-final-Windows/runtime/acceptance.json) | [中文](reports/zh4-final-Windows/runtime/plot-state-zh_CN.json) / [English](reports/zh4-final-Windows/runtime/plot-state-en_US.json) |
| Ubuntu 22.04 AppImage | [中文](reports/zh4-final-linux-0/appimage/gui-zh_CN.png) | [English](reports/zh4-final-linux-0/appimage/gui-en_US.png) | [JSON](reports/zh4-final-linux-0/appimage/acceptance.json) | [中文](reports/zh4-final-linux-0/appimage/plot-state-zh_CN.json) / [English](reports/zh4-final-linux-0/appimage/plot-state-en_US.json) |
| Ubuntu 22.04 DEB | [中文](reports/zh4-final-linux-0/deb/gui-zh_CN.png) | [English](reports/zh4-final-linux-0/deb/gui-en_US.png) | [JSON](reports/zh4-final-linux-0/deb/acceptance.json) | [中文](reports/zh4-final-linux-0/deb/plot-state-zh_CN.json) / [English](reports/zh4-final-linux-0/deb/plot-state-en_US.json) |
| Ubuntu 24.04 AppImage | [中文](reports/zh4-final-linux-1/appimage/gui-zh_CN.png) | [English](reports/zh4-final-linux-1/appimage/gui-en_US.png) | [JSON](reports/zh4-final-linux-1/appimage/acceptance.json) | [中文](reports/zh4-final-linux-1/appimage/plot-state-zh_CN.json) / [English](reports/zh4-final-linux-1/appimage/plot-state-en_US.json) |
| Ubuntu 24.04 DEB | [中文](reports/zh4-final-linux-1/deb/gui-zh_CN.png) | [English](reports/zh4-final-linux-1/deb/gui-en_US.png) | [JSON](reports/zh4-final-linux-1/deb/acceptance.json) | [中文](reports/zh4-final-linux-1/deb/plot-state-zh_CN.json) / [English](reports/zh4-final-linux-1/deb/plot-state-en_US.json) |

视觉观察：十张图均能看到实际蓝色非空波形、约 32 秒和 65 秒处的脉冲组以及可读的中英文界面。**CI 虚拟屏幕裁掉部分窗口右／下边缘；Windows 任务栏覆盖下沿，所以这些 PNG 不构成完整窗口布局验收。** 未将裁切图冒充全窗口截图。

补充实际桌面观察（2026-10-20 08:58–09:02 UTC）：从此 run 下载未改动的 AppImage，独立核对原包哈希，在独立 Linux 云端桌面分别用全新配置以 `--language zh_CN` / `en_US` 加载同一中文路径布局。两次首次打开即出现完整波形，无移除／重加曲线、手动缩放或数据操作。完整窗口观察完整显示 1180×812 主窗口，包括右侧工具条和底部回放控件；两种语言的 560×400 外观首选项也完整可读。此次补充全窗口观察未保存为可下载的截图工件，因此不提供其 PNG 链接或哈希，也不代替最终截图复核。命令行语言覆盖不改写首选项中的持久化默认语言。

另附原生 Windows 构建阶段的 [中文首选项](native-windows/preferences-zh_CN.png)、[英文首选项](native-windows/preferences-en_US.png)、[中文空主窗口](native-windows/main-window-zh_CN.png)、[英文空主窗口](native-windows/main-window-en_US.png)。它们是同一源码的补充语言证据，**不是最终安装器的 BIN 曲线验收替代品**。

## 测试结果及边界

- Linux 原生 CTest：3,433 个注册用例，0 失败，38 跳过。Windows 候选 CTest：3,424 个注册用例，0 失败，73 跳过。跳过不计为通过。Linux 所需 GL 上下文恢复及 raster text GL 用例实际通过。
- 两平台关键 FileLoader 终止发布回归、PlotStateDump 回归、中英文 ArduPilotLayoutRestoreTest 均通过；Windows 测试日志已逐项检查。
- Windows 最终安装器的 19/19 插件加载；Linux 21 项插件清单中 20 项加载。ROS 2 subscriber 因干净环境未安装外部 ROS 2 被明确记为 `not_tested_missing_external_dependency`，不是通过或悄悄忽略。
- 五个最终包安装环境均检查版本、CJK 字体、许可证、Python 后端、插件清单、真实 BIN、中文路径及有限可见采样。
- 本地 Python／静态检查：包验收22、分支3、翻译检查器9、版本／提升5、DEB 依赖2，均通过；翻译 1,228/1,228、provenance、Python 语法及 whitespace 通过。本机没有重复进行 Qt/C++ 构建，原生测试结果来自上述确切 CI。

## 已提升的原始候选包字节

| 文件 | 大小 | SHA256 |
|---|---:|---|
| `PlotJuggler-4.0.0-zh.1.rc.1-x86_64-zh-CN.AppImage` | 159988216 | `8718593df9ede797dfadfc0e6668771af354cae785b2752dbb50da4363e39cca` |
| `plotjuggler4_4.0.0~zh.1~rc.1-1_amd64-zh-CN.deb` | 121232444 | `db846729c41a629ba5991b7f7eeae115d168da6ddcc36afbd352a7412ff7417c` |
| `PlotJuggler-4.0.0-zh.1.rc.1-Windows-x64-zh-CN.exe` | 135239901 | `1a9433c13c3ecc845910a419fe237fffa0986b3a0bdbcb58b1011f5969085cc7` |

Windows EXE、AppImage 和 DEB 原包均已从公开地址匿名完整下载，大小和 SHA-256 与上述候选值一致；AppImage 另有实际桌面补充观察。公开 DEB 下载名为 `plotjuggler4_4.0.0.zh.1.rc.1-1_amd64-zh-CN.deb`，其字节未变。请使用新增的 `SHA256SUMS-public-filenames.txt` 校验实际下载名，原 `SHA256SUMS.txt` 作为上传前候选名称记录保留。

## 发布结果

已通过普通合并进入开发线与发布线，标签固定原候选，并公开原包为预发布。原发布工作流在公开后的文件名校验步骤失败，该事实保留；后续只追加匹配公开文件名的新校验清单及说明，没有重建、覆盖或更换任何原附件。详见 [最终发布记录](PUBLICATION.md) 与 [机器可读校验收据](publication-receipt.json)。

此证据分支未合入已验候选，不改变候选树身份。3.x、上游镜像、197 个旧标签、四个旧版本及其 28 个资产均保持原值；Latest 未改变。
