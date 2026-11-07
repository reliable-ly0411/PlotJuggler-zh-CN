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

## 纯上游镜像自动同步

`main` 对应官方 `PlotJuggler/PlotJuggler:main`（3.x），`main-4.x` 对应官方
同名 4.x 分支。两个镜像保持精确的上游提交，不加入汉化、策略文件或同步脚本。

默认分支的 `.github/workflows/upstream-mirrors.yml` 每 6 小时（UTC 00:13、
06:13、12:13、18:13）检查一次；修改该工作流或其控制器时也会运行。
手动入口的 `dry_run` 默认为 `true`，只读比较；明确取消勾选后才更新镜像。
GitHub 定时任务可能延迟，连续长期无活动时也可能被平台停用，应查看 Actions 结果。

控制器仅在目标是对应上游提交的祖先时快进，不生成合并提交、不强推、不创建或删除
分支，也不修改保护规则。遇到本地独有提交、上游改写、分支缺失、权限错误或已检测的
目标并发变化时，停止受影响分支并使任务失败，保留报告供审阅；另一条安全镜像仍可继续。
最终写入也必须通过 GitHub 原子的非强制更新检查，不丢弃并发增加的历史。失败或结果
不确定的写入在本次运行内不会重试；下次运行先重读实际 ref。报告保留更新前、上游与
更新后 SHA。每次同步对应本次读取的上游快照，之后新到的上游提交由下一次检查接续。

工作流使用本次运行的短期 `GITHUB_TOKEN`，不配置 PAT 或新凭据。由该 token 更新 ref
不会触发其他 push 工作流，因此不会因镜像同步运行上游构建、部署或发布流程。
不签出或执行新同步的上游代码，不动标签、Release、附件或汉化稳定/开发分支。
其他功能、诊断、CI、发布状态分支按各自用途保留，不作为同名上游镜像批量改写。
汉化开发线仍由独立的 `zh-source-sync.yml` 合并并校验；镜像同步不代表汉化晋级或发布。

安全回归：`python3 .github/sync/test_sync_mirrors.py`。
本地只读比较：`python3 .github/sync/sync_mirrors.py --report /tmp/upstream-mirrors.json`。
