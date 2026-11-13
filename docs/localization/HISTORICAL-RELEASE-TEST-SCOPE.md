# 历史发行版与现代开发线的测试边界

`release-4.1.0-historical-scope.json` 明确记录 `v4.1.0+zh.1` 对应源码
`0113492d7a7f96e486de1f9adcde6e43893ab630` 的上游基线、重建插件、核心插件
及 BIN 测试序列数。它不是当前开发线的 SDK/Qt 配置，不授权复用旧包的验收结论。
保留其中当时的状态字段原文，不将当时的待验收描述冒充本次运行状态。

- `test_upstream_release_baseline.py` 对指定历史 Git tree 验证 52 个文件边界及
  原始字节、原始发行说明摘要。历史 scope 的 baseline、插件列表、核心插件列表和
  BIN 序列数均回查历史源码，不能用手工改 scope 消除差异。
- 当前开发线允许后续上游功能；不将现代源码倒退到 4.1.0 以满足历史断言。
  `test_release_notes_consistency.py` 将已发布说明和历史 scope 比较，仍核对当前
  翻译目录消息计数、打包核心集合完整性与结构。现代包依赖、插件可加载性与 GUI
  验收仍由当前打包测试、构建测试和平台验收负责，历史说明不能替代这些验收。
- Debian 测试保留真实 ELF 的未知依赖拒绝检查和 readline alternatives 检查。
  现代上游已经支持 Wayland，所以新增行为以真实 ELF 和生成 deb 的 Depends
  字段验证 `libwayland-client0`，不再套用旧发行版禁止 Wayland 的边界。
- Git 源码压缩包或浅克隆若不含以上历史提交，历史 tree 检查明确跳过并报告缺失
  历史；这不算历史验收通过。完整历史 CI 应保留该提交再运行测试。JSON/发行说明
  内容检查仍可运行；该历史跳过不影响当前开发版必须通过的原生/成品验收门禁。

本次适配验证：6 项历史基线测试、4 项说明一致性测试、3 项 Debian 真实 ELF/
打包测试通过。本次未编译 PlotJuggler、未运行 GUI、未生成/验收正式发行包。
