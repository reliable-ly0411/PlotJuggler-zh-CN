# 4.x 汉化分支与历史规则

本分支基于官方 `main-4.x`，与 Qt5 的 `zh-CN` / `zh-CN-dev` 独立。

| 分支 | 用途 |
| --- | --- |
| `main-4.x` | 官方同名分支的精确镜像，仅安全快进 |
| `zh-CN-4.x` | 稳定汉化线，只接收充分验证后的开发线合并 |
| `zh-CN-4.x-dev` | 4.x 开发集成线 |
| `zh-CN-4.x-feat/<topic>` | 独立功能 |
| `zh-CN-4.x-fix/<issue>-<topic>` | 与 issue 对应的修复或未完成诊断 |
| `zh-CN-4.x-ci/<topic>` / `zh-CN-4.x-docs/<topic>` | 构建、CI 或文档专项 |

两条长期线最初均指向记录的真实上游提交；初始化稳定线不表示汉化已经验收。
主题分支通过保留提交的 merge commit 进入开发线，开发线再通过独立审阅和验证
进入稳定线。不 squash、不改写已公开提交、不强推、不删除历史版本。
`zh-CN-4.x/<topic>` 会与长期 ref 冲突，禁止使用。

上游基准和 3.x 移植来源见
[upstream-baseline.json](localization/upstream-baseline.json)。采用模块级移植，
不会将整条 Qt5 历史合入重写后的 Qt6 主线。3.x 的 Issue #3 / PR #6 尚未解决的
图像诊断不作为 4.x 修复引入。

`Chinese 4.x development checks` 只读运行分支/版本/翻译检查、Qt 原生语言测试、
应用构建与回归；草稿 PR 同样执行检查。它只上传测试报告，不创建 tag、Release
或生产发布资产。上游原有发布工作流不用于本次汉化开发交付。

开始工作前执行 `python3 scripts/check_branch_name.py <branch>`。
仓库级 CI 校验不是服务器分支保护；此规范不改变仓库安全设置。
