# PlotJuggler 简体中文与 ArduPilot 版本

本分支对应本机使用的 Qt5 PlotJuggler 3.17.2，初始基线为官方
`3.17.2` 标签（`034a5cc919909aebb124e0dc1abbe2029c3eed0f`）。
官方主项目已发布 Qt6 的 4.0.0；其插件接口与 3.x 不兼容。
这里仅同步官方 `main` 的 3.x 维护线，禁止自动跨到 4.x。

## 使用

解压 Windows portable 包后运行 `plotjuggler.exe`。安装器默认安装到
`PlotJuggler-zh-CN` 独立目录；配置也使用独立应用标识，不覆盖原版设置。
文件名和安装路径均不要求使用中文。

默认使用简体中文。通过“帮助 → 语言 → English”切换并重启，或直接运行：

```text
plotjuggler.exe --language en_US
plotjuggler.exe --language zh_CN
```

版本号采用 `3.18.0-zh.3+upstream.3.17.2.apbin.1.g<提交号>` 形式：3.18.0 是兼容新增功能的 fork 次版本，zh.3 是第三个先行候选，
加号后的信息标明官方基线、解析修订和源码提交，符合 SemVer 2.0.0。
构建信息不参与版本优先级比较；已发布标签和包不得覆盖，后续功能或修复必须递增适当版本。
Qt Installer Framework 内部组件版本采用数字先行版 3.18.0-3；程序和文件名显示完整 SemVer。包内 `BUILD-INFO.json` 记录准确源码提交和解析器版本。

最新已发布版本为 `3.18.0-zh.2`。本次仅修复启动图的中文嵌字方式，API、CLI、配置与布局文件格式保持兼容，
仍处于同一 `3.18.0` 开发周期。按用户明确要求，本对话的图库及补充修复统一归入尚未正式发布的 `zh.3`，
统一标签应指向包含所有补充改进的最终提交，不为本轮补充另增先行编号；已发布的 `zh.2` 标签及制品保持原样。
本次提交不等于已发布新的安装包；发布仍需对应提交的构建及验收结果。

## ArduPilot 解析范围

默认构建并随包提供独立共享插件 `DataAPBin`。启动时沿用 PlotJuggler 的
插件自动发现机制，第一次打开 `.BIN` 文件时无需手动安装插件。
该功能并非自动连接飞控，也不是 MAVLink 遥测解析器。

解析源码来自 [ArduPilot 官方插件](https://github.com/ArduPilot/plotjuggler-apbin-plugins)，
固定提交 `3e2f9253adc2d41e17b2f0fec74f4b2487c42fb0`，保留原作者信息和 LGPL-3.0。
应用本身保留 MPL-2.0；插件仍单独动态链接，源码位于
`plotjuggler_plugins/DataLoadAPBin`，许可证随二进制一并提供。

- 支持 DataFlash 二进制 BIN 的 FMT、FMTU、UNIT、MULT、TimeUS 和字节实例标记。
- TimeUS 统一转换为秒；有有效 GNSS 时间信息时沿用官方插件的时间同步逻辑。
- GNSS 同步先使用原始 GMS 毫秒值，再应用显示倍率，避免时间被重复换算；使用合成 GPS 周/周内时间验证，不包含坐标。
- GPS/UTC 闰秒差沿用官方插件的固定 18 秒，2017 年以前的绝对时间需要另行校正；相对 TimeUS 不受影响。
- 默认显示单位，按 FMTU/MULT 应用倍率。没有单位/倍率元数据的旧日志保留原始数值。
- 保留官方参数、状态文本和消息说明功能；参数序列使用真实 TimeUS 时间，兼容无 Default 字段的旧 PARM；增加重复加载时的完整状态清理、
  FMT 长度检查以及 128～255 实例编号的处理。
- 不支持 DataFlash 文本 `.log`、仅有 TimeMS 的旧记录，以及 ISBH/ISBD
  批量惯性数组波形。字符串/数组字段不会伪装成数值曲线。
- 64 位整数作为 double 曲线显示，绝对值超过 2^53 时可能损失整数精度。

可以关闭此插件，其他格式的加载器保留：

```text
Windows: plotjuggler.exe --disabled_plugins DataAPBin
Linux:   plotjuggler --disabled_plugins libDataAPBin
```

源码构建时使用 `-DPJ_BUILD_ARDUPILOT=OFF` 可完全排除它。
单位标签是序列名称的一部分；与不带单位的旧插件布局互换时需重新绑定曲线。

## 翻译维护与已知边界

Qt `.ts` 为唯一翻译来源，构建时通过 Linguist 编译并嵌入 `.qm`。
当前覆盖主菜单、对话框、设置、常用插件、错误提示和帮助内容。
技术标识、快捷键、协议名、格式表达式和用户数据保持原样。

第三方运行时异常文本、用户消息内容、ArduPilot XML 字段说明、插件返回的
动态名称以及诊断标准输出可能仍为英文。这些内容不会被盲目替换。
Qt 标准对话框优先使用随包或系统 Qt 的 `qtbase_zh_CN` 翻译。

```text
lupdate plotjuggler_app plotjuggler_base plotjuggler_plugins -no-obsolete -ts plotjuggler_app/translations/plotjuggler_zh_CN.ts
python tests/check_translations.py --fresh
```

`--fresh` 重新提取到临时文件，新增未翻译消息和丢失的 `%1` 等占位符会令检查失败。
本分支不发送机器标识或使用遥测。

## 同步和自动构建

`zh-sync.yml` 每日 03:23 UTC 以及手动触发。它将官方 `main` 合并到 `zh-CN`，
保留定制提交，不使用强推、重置或自动选择冲突一方。
冲突、版本跨代或翻译校验失败时，取消本次合并，保留远端定制分支，
Actions 标红并上传 JSON 报告及冲突文件列表。
上游 `.github/workflows` 的变化不会自动导入：本 fork 的自动化保持独立，变化会列入
`held_workflows` 供人工审核，因而无需额外的 workflows 权限或 PAT。没有上游变化时成功返回 `up_to_date`。
推送竞争通过普通 Git push 拒绝处理，需查看报告后重试。

GitHub 调度可能延迟；公共仓库连续 60 天无活动时，GitHub 会暂停定时工作流，
届时需在 Actions 页面重新启用，详见 [GitHub 调度说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

同步任务只使用仓库临时 `GITHUB_TOKEN` 的 `contents:write`。构建任务仅需
`contents:read`，不使用 PAT，不向第三方授予权限，不运行外部 PR 的特权脚本。
官方其他工作流保留在源码中，但仅在官方仓库运行。

`zh-windows.yml` 构建 Windows x64 安装器和 portable 包；`zh-linux.yml` 构建
Linux x86_64 AppImage。两者复用上游 Qt5 构建/打包方法，使用 GitHub 公共 runner。
普通提交和 PR 自动构建；同步提交通过可复用工作流显式构建，避免依赖
GITHUB_TOKEN 推送无法再次触发工作流的行为。

构建成功还必须通过合成 DataFlash 测试、翻译检查和中英文真实窗口截图验收，
之后才上传包和证据。工作流配置已提交不等于构建成功；以对应 Actions 运行结果为准。

## 本地构建和验收

沿用上游 CMake/Qt5 工具链，额外需要 Qt LinguistTools 与 Python3。
fork 验收测试默认开启，可用 `-DPJ_BUILD_FORK_TESTS=OFF` 关闭（兼容早期的 `PJ_BUILD_ARDUPILOT_TESTS` 开关）。
覆盖 DataFlash、SemVer 和合成 Parquet 读取；Linux 统一使用共享 Arrow/Flight，避免插件间重复注册 Protobuf 描述符。

```text
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
python tests/test_sync_upstream.py
```

测试日志均为合成数据，不包含飞行记录、位置、硬件信息或用户文件。
Git 同步保护测试使用一次性临时仓库，不接触用户的其他仓库。


## zh.2 界面补全与启动图库

工具菜单的四个常用插件在中文模式中显示「中文（English）」，插件内部名称与布局文件标识保持原样。
Mosaico 的列表表头、日期预设、加载状态、元数据、下载统计、错误提示及上午/下午显示均进入 Qt 翻译目录。
上午/下午的计算继续使用稳定的 AM/PM 数据值。MSVC 以 UTF-8 编译，避免省略号和箭头出现乱码。
Qt5 标准按钮的简体中文翻译随应用嵌入，不依赖用户另装 qtbase 中文语言包。

「帮助 → 向汉化项目报告问题」打开本分支的反馈表单。
关于页同时显示中文与英文，保留上游作者、许可证、商业支持联系方式，并添加汉化仓库和报告入口。

### zh.3 启动图库：AI 嵌字与补充重试

启动图库保留全部 106 张英文原图。98 张含待译文字的图片使用内置 image_gen 工具逐张尝试编辑，
最终采用 88 张经过人工查看的中文图：移除原英文笔画、描边与阴影，修复下方画面纹理，再将中文直接嵌入图片。
中文资源位于 `plotjuggler_app/resources/memes/zh_CN/meme_*.png`，通过 Qt 资源系统随应用打包。
另外 8 张仅含产品或技术名称，中文模式也使用原图；英文模式始终使用未修改原图。
产品名、代码/信号标识、公式和原图署名按原图保留；图库版权继续归原权利人。

实体上的文字需与材质和透视一致：第 3 张的路牌字、第 30 张的红色名牌字、第 64 张的纸板字及第 98 张的计时牌红字，
分别补充路牌印刷、照片焦外柔化、马克笔和旧漆质感。衣服、箱体、砖墙等已有合适效果的文字经复查保留。
普通叠加字幕维持原有样式，包括第 98 张下方的白字黑边字幕。

第 2 张本轮重试成功，中文、原图署名和实际启动尺寸均经复查，已加入中文图库。
第 6、10、21、33、41、51、54、56、69 张再次正常重试后仍返回 `moderation_blocked`，保留原图，不叠加中文或遮罩。
最近一次返回的审核阶段均为 `output`，第 51、69 张的类别为 `sexual`，其余为 `other`。
这些是服务对生成结果返回的类别，并非对原图内容的判断；服务未提供更具体原因，不能推断具体触发元素。
第 105 张本轮 8 次请求中，6 次返回 `network error: error sending request`，2 次只完成主标题，未形成完整中文图，因此仍保留原图。
已检查 JPEG 解码、零 JFIF 密度、像素不变的元数据规范化副本及程序导出的完整 PNG；单一主标题请求在 JPEG 和 PNG 输入上均曾成功。
后续两块实体牌、单块实体牌和校正后的完整译文请求仍返回传输错误。没有证据能将故障归因于文件格式、元数据或某条提示词，服务也未给出更详细诊断。
另校正提示词中与原图不一致的菜单和标签页名称，保留技术源标识；仅有主标题的中间图不计入中文资源。
所有原始 JPG 保持不变。`zh_CN.json` 记录最新错误，完整重试提示词、错误码、请求编号和输入诊断保存在 `meme-ai-prompts.json`。

运行时直接加载图片，不再用 QPainter 填充矩形或绘制文字，也不依赖系统字体、Python、在线 AI 或额外下载。
图片仅按原启动图尺寸等比缩放。AI 修复的画面局部可能与原素材略有差异，英文原图可随时对照。
`zh_CN.json` 保留 197 个区域的原文、译文及位置作为维护依据，并记录原图和中文图 SHA256。
第 105 张原先误列为待译文字的 `live_websocket` 是源标识，现已移出译文区域并明确保留原样；菜单和标签页译文按原图校正。
区域和 style 字段不再参与运行时绘制；修改 JSON 中的译文后，还需重新生成并审核对应中文图片、更新哈希。
本次完整提示词保存在 [meme-ai-prompts.json](meme-ai-prompts.json)。

`plotjuggler --language zh_CN --export-memes output-directory` 继续导出全部 106 张及 JSON 报告。
报告原有 `text_fits` 字段为兼容保留，现在表示图片资源加载有效，不再表示字体测量或替代人工文字检查；
新增 `rendering` 与 `asset` 字段说明实际图片来源。标记为 `original-ai-unavailable` 的 10 张是明确允许的原图回退；
其他缺失的中文资源会警告并回退原图，导出验收同时失败。
`tests/check_memes.py` 检查 88 张中文资源注册、10 项回退记录、全部原图及哈希；`LocalizedMemes` CTest 检查图片像素与内嵌资源一致、
系统字体变化不影响图片、英文像素保持一致，以及两种语言的全部导出。

本地使用 Qt 5.15.13 编译生产资源与加载代码，通过上述回归检查、212 张中英文导出及 9 张 QSplashScreen 离屏截图复查；
另通过翻译占位符、图库完整性、版本一致性和 6 项同步保护测试。完整程序的本机构建因缺少 Qt5Svg 开发包未完成，
离屏截图也不代表完整程序的桌面验收；Linux/Windows 完整构建、打包及真实窗口验收以本次提交对应的 Actions 结果为准。

本次验收与发布记录归档于 [Issue #1](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues/1)。
用户要求报告归档完成后再清理本机构建缓存；安装回退备份独立保留。
