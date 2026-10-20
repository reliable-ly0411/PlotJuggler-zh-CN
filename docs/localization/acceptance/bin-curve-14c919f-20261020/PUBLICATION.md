# 最终发布与匿名下载复核

[预发布 v4.0.0-zh.1.rc.1](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/v4.0.0-zh.1.rc.1) 已公开，不设为 Latest。标签仍精确指向 `14c919f903936130c151818dbf1a0144ea6a6050`；原包来自成功候选 run `39390859457`、attempt `1`，没有重新构建。

## 来源与合并

- PR #8 普通合并进入 `zh-CN-4.x-dev`：`4fb7c5b63775dbd528434319ecc78573a1c1c94c`。
- PR #9 普通合并进入 `zh-CN-4.x`：`316af98910377b202913520539e40bca3b3496a5`。
- 两个 merge commit 的树均为候选树 `b35df58b136a50c19026bd2cd866bcf8c082f866`；原候选提交保留为祖先，发布 tag 指向原候选，而不是另一个未经验收的构建。
- 本文档分支独立于发布源码树，仅保存证据。

## 文件名事件与追加修正

[原发布流程 39400241199](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/actions/runs/39400241199) 已创建 tag 并公开原包，但随后公开下载校验失败。原因是 GitHub 将 Debian 附件名中的 `~` 改成 `.`，原 `SHA256SUMS.txt` 仍列上传前名称。此 run 保持失败，不重跑、不改写为成功。

Windows EXE、AppImage、DEB 和原校验文件均已通过公开地址无凭据完整下载。三个包的大小及 SHA-256 与已验候选 manifest 一致。DEB 内部版本仍为 `4.0.0~zh.1~rc.1-1`，仅公开附件名不同。

仅新增 [SHA256SUMS-public-filenames.txt](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/download/v4.0.0-zh.1.rc.1/SHA256SUMS-public-filenames.txt) 并在原发布说明末尾追加解释；没有删除、替换、重命名原附件或移动标签。新清单资产 ID `658887297`，345 字节，SHA-256 为 `6af13ad89cc2e3e2dd4287552d7ac5c8f4d2000f5db87b21f6e91a50c5a38222`。独立匿名下载新清单后，对实际公开下载文件名执行 `sha256sum -c SHA256SUMS-public-filenames.txt`，三个包全部为 `OK`，退出状态 0；[完整结果](checksum-verification.txt)。

## 不可变性与说明

- 原四个附件的 ID、名称、字节数、SHA-256、创建及更新时间完全保留。
- 197 个旧 tag、四个旧 Release 及其 28 个附件保持原值。
- 本版仍为预发布；Latest API 在前后均返回 404，未将开发候选设为正式版 Latest。
- 原发布说明内容（包括上游 4.0.0 全文）完整保留。网页表单将 LF 换行为 CRLF，除此以外只增加预定说明段落。
- 完整机器可读记录见 [publication-receipt.json](publication-receipt.json)。候选截图、原始报告、采样和裁切限制仍见 [README.md](README.md)，不将裁切截图冒充全窗口截图，也不将 ROS 2 未验项记为通过。
