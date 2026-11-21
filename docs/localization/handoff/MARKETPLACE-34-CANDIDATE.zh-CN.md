# 34 项市场目录修复候选

关联 [#71](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/71)。基线 `d7109d0fd9e40e139adab55be9eb66da283e9013`；分支 `zh-CN-4.x-fix/71-marketplace-catalog`。

## 改动

- 固定 registry 已扩展为 34 项，目录测试保持精确计数断言并更新为 34。
- 补齐 candump-loader、influx-parser、log-widget、navmap-parser 的名称和说明，共 8 条简繁译文。只改变显示，不改变插件 ID 或来源匹配。
- 刷新 Qt 提取位置和计数文档，两种中文各 2,159 条活跃消息。

## 已执行验证

- 分支名称、git diff --check 通过。
- Qt 6.11.1 lupdate 重新提取：简繁均 2,159/2,159，缺失、陈旧、未完成均为 0；占位符、复数、富文本、上下文检查通过。
- test_check_translations_4x.py：11/11；test_reviewed_translation_terms.py：1/1。

## 待验收

尚待产品固定 Qt 6.12 的 Linux/Windows MarketplaceCatalogTest、包装和干净安装验证。先读取基线现有运行最终日志，再选择必要回归，不复用旧 head 验收结论：

- [源码 44208920259](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44208920259)
- [WASM 44208920282](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44208920282)
- [原生包装 44208963979](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/44208963979)

本分支仅保存源码和验证记录，不晋级开发/稳定线，不发布。浏览器性能与最终包验收仍由 #71 跟踪。
