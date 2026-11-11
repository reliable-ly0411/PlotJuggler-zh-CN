# Qt5 / 3.x 来源与许可清单

原版权归各作者所有。汉化、启动器与新增测试沿用本仓库 MPL-2.0；
这不改变第三方代码、Qt 译文和图片的独立许可。本文件是工程清单，不把动态链接视为自动完成全部发行义务。

| 内容 | 固定来源/仓库位置 | 保留文本 |
| --- | --- | --- |
| PlotJuggler Qt5 应用 | 上游 `df5cbaad9bb087413470e818fa5cdb88d6357ce5`，声明 3.17.2 | `LICENSE.md`，MPL-2.0，Davide Faconti 等原署名 |
| ArduPilot DataFlash | `3e2f9253adc2d41e17b2f0fec74f4b2487c42fb0`，`plotjuggler_plugins/DataLoadAPBin/UPSTREAM.md` | 独立 LGPL-3.0、GPL-3.0 正文和来源文件 |
| Qt5 Core/Gui/Widgets 等及标准目录 | 构建所用 Qt5；目录摘要写入 `QT5-TRANSLATIONS.json`，不是 Qt6 目录 | Qt 库的 LGPLv3/GPLv3 与 Qt translations 的 GPL3-EXCEPT 原文；Linux 另保留发行版版权文件 |
| Qwt | `3rdparty/qwt` | Qwt License 1.0，含 LGPL 例外 |
| Qt Advanced Docking | `3rdparty/Qt-Advanced-Docking` | LGPL-2.1，原作者署名 |
| color_widgets | `3rdparty/color_widgets` | LGPL-3.0 |
| QCodeEditor | `3rdparty/QCodeEditor` | MIT |
| backward-cpp、date、sol2 | 对应 `3rdparty` 目录 | 各自 MIT 文本与逐文件署名 |
| KissFFT | `plotjuggler_plugins/ToolboxFFT/3rdparty/KissFFT` | 原 `COPYING` |
| Lua、fmt、data_tamer、wasmer、Arrow/Flight、Protobuf、ZeroMQ、Mosquitto 等 | CMake 固定下载版本或 `conanfile.txt`；具体链接/缺失情况以相应构建日志为准 | 保留来源和依赖自身声明；不能由此推断未构建插件随包存在 |
| 启动图与简体衍生图 | `plotjuggler_app/resources/memes` 及来源 JSON | 原权利人署名与来源；代码许可不等于照片授权。繁体仍回退英文原图 |

Qt 5.15.2 的 translations 来源为 [Qt 官方源码](https://github.com/qt/qttranslations/tree/v5.15.2)，
其 [GPL3-EXCEPT 原文](https://github.com/qt/qttranslations/blob/v5.15.2/LICENSE.GPL3-EXCEPT)原样随包保留。
Ubuntu 本机 Qt translations 包为 5.15.13-1，来源为
[Ubuntu 源包](https://launchpad.net/ubuntu/+source/qttranslations-opensource-src/5.15.13-1)。
标准译文未修改；应用自有的按钮译文由应用目录覆盖。构建必须找到匹配 Qt5 的两份标准目录，否则配置失败。
Qt 5.15.2 官方 Windows 包的简体译文仍合并在 `qt_zh_CN.qm`，构建兼容该原始文件；
繁体使用 `qtbase_zh_TW.qm`。实际选用的文件名与 SHA256 均写入包内清单，
标准按钮和文件对话框的翻译仍须通过测试。

每份包包含 `BUILD-INFO.json`（完整源码提交、上游 SHA、版本、解析器来源），
以及 `Licenses` 下的应用、解析器、Qt 和上述随源码保留的许可文本。
应用和本轮修改的完整源码位于该 `commit` 对应的 GitHub 树；原文件头和独立许可证保留在源码中。
发行版动态系统依赖与 Windows/AppImage 所捆绑的运行库范围不同，验收时应按实际包清单复核。
