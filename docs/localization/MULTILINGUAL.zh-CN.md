# 多语言开发：繁體中文（台灣）

这是 `zh-CN-4.x-dev` 的开发功能，基于开发线 `9f38ffd4bd625723ef96c8a49ad320846b98bc2b`。
它不修改已发布 rc.3 的字节、标签、稳定分支、包名或安装路径，也不表示新版本已发布。

## 使用方式与 locale

首选项提供三个始终以本语言显示的选项：

| 显示名 | 保存值 | 本次启动覆盖 |
| --- | --- | --- |
| 简体中文 | `zh_CN` | `--language zh_CN` 或 `--language zh-CN` |
| 繁體中文（台灣） | `zh_TW` | `--language zh_TW` 或 `--language zh-TW` |
| English | `en_US` | `--language en_US` 或 `--language en-US` |

新配置仍默认简体中文。点击确认才保存下次启动语言；取消不保存，也不重新翻译当前窗口。
命令行覆盖只影响当前会话，不改变首选项。未知值回退英文源文，但不覆盖原有设置。
`zh`、`zh_HK`、`zh-Hant` 和带编码后缀的 locale 未声明支持，不推断成台湾或大陆中文。
繁体目录采用台湾用语，而不是宣称覆盖香港、澳门或所有繁体地区。
数值、日期/数据解析使用的 locale 不因界面语言改变。

应用将 `zh_CN`、`zh_TW` 两份 `.qm` 与相应 Qt 标准对话框译文编入资源，离线运行无须语言包下载。
每份主目录当前有 2,020 条可提取消息、26 条单复数消息和 29 条保留标识/格式串。
其中 FFT 1.0.1 的后续开发覆盖和三语回归见[插件反馈回归](PLUGIN-FEEDBACK.zh-CN.md)；
下方 2026-10-24 的历史验证数字保留当时结果。
完整源键覆盖不等于所有第三方、系统或栅格图片文字都已本地化。

## 覆盖与安全边界

- 主窗口、首选项、绘图、2D/3D 场景、插件市场、固定随包插件对话框和内置滤波器显示文本使用同一启动目录。
- 采用「檔案、資料夾、儲存、載入、匯入／匯出、偏好設定、外掛程式、記憶體、執行緒、滑鼠、捲動、訊息」等台湾界面术语。
  目录以既有简中语义为基础建立初稿，再做术语与重点内容校订；不宣称每条都经过台湾母语用户或全界面视觉验收。
- 英文源键、插件/主题/滤波器 ID、URL、格式通配符、菜单动作 ID、路径、数据列名、代码与用户输入不做简繁转换。
  插件显示层继续使用固定 UI 哈希、控件属性和固定版本门槛；未知插件内容保留原文。
- 五个固定来源重建插件的内部固定文案新增繁中版本。`PLOTJUGGLER_UI_LANGUAGE` 只携带规范界面代码，
  在插件首次使用时形成不可变选择，不改协议或持久化配置。Windows 仍只使用其中四个，Assistant 为 Linux 专属。
  Mosaico 保留官方二进制及既有英文混合正文边界，未启用延后补丁或扩大 SDK 支持声明。
- 简中启动趣图仍为原有 41 项，英文原池不变。繁中仅使用 8 组无文字底图与繁中动态字幕组合，
  不混入简中像素字幕图片。趣图／严肃横幅选择仍保留，原有简中趣图历史不会使繁中挑中简中图片。
- Windows IFW 安装／维护向导仍仅支持简中和 English。安装完成后在应用首选项选择繁中，
  或以 `PlotJuggler4.exe --language zh_TW` 启动。向导语言不会冒充应用语言，也不会自动迁移设置。
  IFW 标准页、重启切换及包名/路径本轮不变，详见[安装器说明](../../packaging/installer/README.zh-CN.md)。
- 浏览器持久化白名单只增加规范 `zh_TW`，不接受别名、任意键或路径；这不是完整 WebAssembly 浏览器验收。

## 开发与回归

新增语言需同步 `AppLanguage::supportedLanguages()`、CMake TS 列表、浏览器规范代码白名单和检查器 `CATALOGS`。
原生插件还需增加独立固定文案、选择器及离线测试。不要依赖运行时字形转换替代独立目录。
菜单 endonym 不随当前语言翻译，避免用户切换到不认识的语言后找不到原语言。

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s .github/release_policy -p 'test_*.py' -v
python3 tests/check_translations_4x.py --lupdate /path/to/qt/bin/lupdate
python3 tests/check_localization_provenance.py
python3 scripts/check_branch_name.py zh-CN-4.x-feat/traditional-chinese
cmake -S pj_app/tests/i18n -B build-i18n -DCMAKE_PREFIX_PATH=/path/to/qt
cmake --build build-i18n
ctest --test-dir build-i18n --output-on-failure
cmake -S 3rdparty/plotjuggler-apbin-plugins/sdk4 -B build-bin-parser
cmake --build build-bin-parser
ctest --test-dir build-bin-parser --output-on-failure
```

翻译检查默认检查两份目录；`--language zh_TW` 可仅检查或配合 `--update-ts` 更新繁中。
`--catalog-only` 不做源代码覆盖验证。新翻译必须通过占位符数量、单复数、富文本及链接属性检查，
固定插件过滤器通配符与动作 ID 还有单独回归。
原生插件辅助测试通过 `tests/test_native_display_language.py` 纳入开发检查；缺少本机编译器时明确跳过执行部分。

Qt 专项覆盖两份嵌入目录、三语往返、偏好保存/会话覆盖、数值 locale、插件 UI 的原始数据保留、
浏览器白名单及繁中趣图池隔离。完整应用测试另有真实首选项确认/取消、三语菜单截图、字体和最小布局检查。
独立专项及源代码测试不等于完整 Linux/Windows 应用、所有插件二进制或最终安装包已验收。
发布前仍需针对同一最终提交执行这些完整构建、安装/维护和人工视觉验收，不沿用 rc.3 的结果替代新代码验证。

### 本轮验证记录（2026-10-24，Linux 云工作区）

- Python 源代码回归共 124 项：119 通过，5 项因缺少 Windows/PowerShell 平台能力明确跳过；发布策略测试 4 项通过。
- Qt 6.11.1 专项实际编译后 CTest 26/26 通过；包括生产繁中目录、三语生命周期、浏览器白名单、
  固定插件 UI 数据边界、市场目录、启动趣图、资源链接和既有安装器脚本引擎回归。
- 两份主目录各 1,968/1,968 源键通过 `lupdate` 核对；无缺失、过期或未完成条目。
- 固定 BIN 子模块的解析专项 1/1 通过；这不是完整应用的 BIN 导入/布局恢复或动态 ABI 测试结果。
- 原生插件 123 组固定三语文案与 10 类语言/回退值通过离线检查；真实固定 Assistant/MCAP 源码的显示 fixture 通过，
  六份补丁均通过原始源文件身份核验及 `git apply --check`。其中 Mosaico 仍为延后补丁，不进入产品重建清单。
- 独立复核确认插件文案的原英文与简中参数未改变，并检查了 8 张繁中动态趣图的可读性；不等于全窗口视觉验收。
- 完整应用配置尝试停在缺失 GTest；本环境也未准备完整 Conan 依赖图。完整 Linux/Windows 应用构建、
  主窗口/首选项截图与交互测试、所有原生插件二进制重建、Windows 安装/维护和最终包验收未执行。
  Windows source-check lane 没有 MSVC 环境时，辅助 C++ 执行测试会明确跳过，不能据此声称 Windows 原生执行通过。
