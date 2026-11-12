# 本地许可证材料缺口（候选修复）

本文件记录待核事实，不代表许可证闭包、法律判断或发布批准。

- Wasmer：构建树 `build/_deps/wasmer-src/ATTRIBUTIONS` 与同目录 `LICENSE` 来自同一实际构建依赖。暂存脚本复制两者；若有 LICENSE 却无 ATTRIBUTIONS，则停止，避免静默遗漏。仍须按实际静态链接内容核对所有适用第三方通知。
- Linux 本地 Arrow 26.0.1：已保存的 `libarrow2600`、`libarrow-flight2600`、`libparquet2600` 软件包是 26.0.1-1。其版权文本提及上游 NOTICE 和待核条目；本机尚未找到可核对来源、属于 26.0.1 的完整源码 NOTICE。不得用其他版本代替。后续应获取并验明精确对应源码发行物及其 NOTICE，并核对实际二进制包含项。
- Windows Conan Arrow 21：仅以该构建实际 Conan host 包为准。清单中的 `notice_evidence` 只说明包内同版本 NOTICE 的存在状态；`packaged-unverified` 也必须对照该精确版本源发行物，不表示通过审计。不得把 Linux 26 材料用于 Windows 21。
- Linux `Distro/manifest.json` 仅是构建宿主 ldd 观察；未归属、缺失依赖、查询失败或无法确定准确架构版本须明确列出并标为 incomplete。必须另对最终包内全部 ELF（包括 Qt 插件及私有 SDK）逐字节核对实际来源、版权与版本。原包 125 份版权文件不能单独证明完整闭包。
- Qt、DataFlash 等 LGPL 库的精确对应源码、打包修改及可用获取方式仍待验证。静态链接 LGPL 的 color_widgets 和 Qt Advanced Docking 仍需可用的重链接材料或许可允许的其他方案，并实际验证。主仓库提交 URL 本身不足以证明这些义务已满足。
- 还需按精确构建输入验证 Wasmer 传递依赖与 Apache NOTICE，核对图像权利与署名，以及处理此前包体隐私审计失败。上述任一未完成均不应记作发布许可已通过。
