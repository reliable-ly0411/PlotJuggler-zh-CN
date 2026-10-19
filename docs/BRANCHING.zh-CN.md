# 汉化分支、上游镜像与发布规则

## 长期线与命名

- `zh-CN`：稳定汉化线、默认分支。只接受经过审阅与相应 CI 验证的改动。
- `zh-CN-dev`：汉化开发集成线。上游 Qt5 同步与未完成的诊断先进入这里；测试通过不等于问题已解决。
- `zh-CN-feat/<topic>`：短期功能；`zh-CN-fix/<issue>-<topic>`：关联 issue 的修复。
- `zh-CN-ci/<topic>`：构建、发布工具；`zh-CN-docs/<topic>`：文档。
- `zh-CN-release/<version>`：确有并行冻结或维护需要时使用，例如 `zh-CN-release/v3.18.0-zh.5`。不要为每次发版永久留一条分支。
- `<topic>` 使用小写 ASCII 字母、数字和单连字符；修复 issue 为正整数。
- 禁止 `zh-CN/<topic>`：Git 的 ref 命名会与现有 `zh-CN` 冲突。

官方上游镜像保留原名，明确登记于 `upstream-mirrors.json`。这些分支不是汉化功能分支，不需要合并到汉化线，也不要改名。新增上游镜像先核对官方同名 ref 并审阅清单更新；不要拿上游名称给汉化工作开后门。

`Localization branch policy` 检查送往两条长期线的 PR 和符合前缀的 push。它提供 CI 校验，不等于服务端禁止创建错误命名的分支；当前整理不更改仓库安全/保护设置。协作者应在开分支前执行 `python3 scripts/check_branch_name.py <name>`。

## 2026-10-19 整理映射

| 原名称 | 处理方式 / 目标 |
| --- | --- |
| `zh-CN` | 原名保留，稳定线 |
| 无 | 新建 `zh-CN-dev`，从稳定提交 `4101a6e776a39e49db31627a5e6c6f78ec6b45eb` 起步 |
| `fix/scaled-caption-determinism` | 保留全部 7 个诊断提交；目标 `zh-CN-fix/3-scaled-caption-determinism`，PR 指向开发线，Issue #3 仍未解决 |
| `zh4/resource-overlays` | 已经由 PR #2 合并且树与稳定线相同，不为已完成工作制造新名字 |
| `automation/release-v3.18.0-zh.4` | 历史一次性发布；提取/归档工具至 `scripts/release-tools/`，不把旧发布触发器合入活动 CI |
| `release/backfill-zh-linux` | 同上，其工作已被两个 zh.3 辅助分支包含 |
| `release/backfill-zh3-linux` | 同上，不继续补发旧资产 |
| `release/publish-zh3-existing` | 同上，不继续补发旧资产 |

本次整理使用短期 `zh-CN-ci/branch-policy`。旧 ref 的清理另行确认；在对应 PR 合入、独有工作保留、外部引用检查完成前不删除。用创建新 ref 复制旧 ref 不等于旧 ref 已改名/删除。保留备份也不能代替删除授权。

## 合并与同步

1. 功能和诊断一般从开发线分出，PR 回到 `zh-CN-dev`；稳定修复可以有独立 PR 到 `zh-CN`。
2. 开发线到稳定线用独立、经过审阅的 PR，不为追求仅两条分支而硬合未完成工作。
3. 官方镜像仅允许快进到官方同名 head。逐条核对 SHA/祖先关系；遇分叉停止并报告。禁止 force-push、删除镜像或用汉化提交覆盖镜像。
4. 既有每日 Qt5 上游同步改为目标 `zh-CN-dev`，不会直接推进稳定线。上游 major 变为 4、代码冲突、翻译校验失败时停止。
5. 自动同步脚本保留本仓库 workflow，不悄悄引入上游 CI；其变动仍需人工审阅。镜像同步是另一个独立操作，当前未新增周期性自动同步任务。

## CI 与发布

- `zh-release.yml` 名称保留以减少引用变更，但现在只构建和验证七个平台的软件包；稳定和开发 push/PR、手动运行都不能发布 Release。
- 日常 CI 不监听版本 tag，不具备发布 job 或写仓库权限。历史一次性发布逻辑仅以非执行参考保存。禁止复活其中旧 run/artifact/release ID 和自身分支名。
- 现有打包版本及资产校验仍对应 zh.4，开发构建不应当被称为新的正式版本。下一次发布必须单独修改包版本、资产清单/校验、发布说明及受控发布流程，审阅通过后再操作。
- 已发布 `v3.18.0-zh.1` 到 `v3.18.0-zh.4` 的 tag、Release 和附件保持不变；不得移动、覆盖或重建。`v3.18.0-zh.N` 是 fork 版本，当前历史基线是官方 3.17.2，并非宣称上游已经发布 3.18.0。
- 标签锁定发布源码，Release 承载说明和附件，分支用于持续开发。未来发布需明确授权，源提交必须来自经验证的稳定线；优先新版本，不覆盖旧发布。

## 接手检查清单

开始前读本文件和相关构建说明；刷新远端，保存 refs/SHA 与完整 Git bundle，并验证 bundle。检查旧任务、PR、保护规则、workflow 的分支引用。改动后运行命名测试、同步脚本测试、发布资产/隐私测试、YAML/Actions 校验与涉及平台的 CI。记录验证未运行或失败的原因；不得把诊断仍存在的问题说成已修复。清理临时分支时先确认正常产品恢复能力与当前授权。
