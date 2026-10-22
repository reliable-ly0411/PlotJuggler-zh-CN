# 原生程序独立测试目录

`plotjuggler4 --profile-dir <absolute-directory>` 是同一系统用户下的**显式、可选**测试配置。
它不修改原有用户配置，不创建新账号，也不修改永久环境变量。未传入该参数时，原有
注册表／QSettings 格式、AppData 路径及环境变量覆盖行为全部保持不变。

该选项适用于加入本功能后的原生主程序，不适用于旧版安装包、浏览器版、IFW 安装器或
维护工具。**安装目录与应用 profile 是两回事**：本参数不约束 IFW 的安装注册、快捷方式、
维护工具或卸载行为，也不使“安装一次”变成不改系统的操作。

## 启动示例

先准备一个自己所有的专用测试目录，勿选现有正式配置目录。测试程序、样例、日志、
截图与导出文件也应分别放在同一专用测试工作区内；不要拿正式数据进行写入测试。

Windows PowerShell：

```powershell
& 'D:\PJ4-test\app\bin\plotjuggler4.exe' --profile-dir 'D:\PJ4-test\profile' --language zh_CN
```

Linux（使用已解压的原生程序或 AppImage）：

```sh
./plotjuggler4 --profile-dir /tmp/pj4-test/profile --language zh_CN
```

也接受 `--profile-dir=/absolute/path`。空值、缺值、重复参数、相对路径、不可写目录、
被文件占据的必需目录，以及已发现的 profile 内符号链接／Windows junction 会使启动
失败，退出码为 `64`，不会静默回退到正式用户配置。参数解析遵守 `--` 终止符。
程序可创建尚不存在的根目录；用户明确选择的根本身会规范化为其实际路径。
该检查也用于带 profile 的 `--help`、`--version`、插件验证及 `--selftest-python`。

再次使用同一个目录会保留该测试 profile 的设置和插件状态；切换到新的专用目录则得到
全新的设置。初始化在应用自己的任何 QSettings、WidgetTuner 或插件仓库访问之前完成。
失败可能留下专用目录中的空目录或探测文件，不会转而使用正式配置。

## 隔离范围

令 `P` 为规范化后的 profile 根：

| 内容 | 位置 |
|---|---|
| 默认 QSettings 用户配置 | `P/settings/user/PlotJuggler/PlotJuggler4.ini` |
| QSettings 系统作用域及其后备层 | `P/settings/system/`，仅该 profile 的 INI |
| 市场插件仓库 | `P/data/extensions/` |
| 待提升安装与备份 | `P/data/.extension_staging/`、`P/data/.backup/` |
| 插件事务、工件、解包、状态、profile 回执及写锁 | `P/data/extensions.*` 与 `P/data/.extensions.lock` |
| 源数据缓存 | `P/data/source_cache/` |
| 实时录制 | `P/data/recordings/` |
| HTTP 模型缓存 | `P/data/models/` |
| 内嵌 URDF 资源临时解包 | `P/tmp/urdf-assets-*` |

用户及系统两个 QSettings scope 都切换为 profile 内 INI，不读取原有注册表或生产配置
作为 fallback。通过应用宿主 QSettingsBackend 保存的插件设置也走该 INI。
源缓存和录制目录在 profile 模式下固定，首选项中对应路径只读；即使该 profile 的 INI
手工写入外部目录，或调用方指定外部目录，应用服务仍使用 profile 内路径。
`PJ_MODEL_CACHE_DIR` 也不能覆盖显式 profile。Qt OpenGL shader disk cache 在该模式下禁用。

`--plugin-dir` 只改变插件发现优先级，不等价于 profile，也不把默认市场仓库移到该目录。
带 profile 时，默认市场仓库及每次启动的随包插件同步均在 `P/data/` 内。

## 不是安全沙箱

- 布局保存、导出、截图、诊断输出以及明确指定的插件目录仍服从用户选择；测试时必须
  另外把这些路径指向专用工作区。profile 不重写输入文件，也不阻止读取外部样例。
- 任意外部插件、脚本、子进程、Qt 平台后端、操作系统和显卡驱动可能使用自己的路径。
  profile 不提供系统级文件访问隔离，也不承诺整个进程绝无 profile 外写入。
- 它用于自己的专用目录，不防御恶意硬链接、启动后的并发路径替换或其他本机攻击者。
  不要复用不可信目录；启动检查会拒绝已有的子目录符号链接／junction。
- 本功能不迁移、不删除正式配置，也不会自动清理测试工作区。清理前应退出使用该
  profile 的所有进程，并确认所选目录确实是自己的测试目录。

## 回归入口与证据边界

Qt 6.11.1 独立测试无需完整 SDK：

```sh
cmake -S pj_app/tests/profile -B /tmp/pj-profile-tests -DCMAKE_PREFIX_PATH=/path/to/Qt/6.11.1/gcc_64
cmake --build /tmp/pj-profile-tests
ctest --test-dir /tmp/pj-profile-tests --output-on-failure
```

Windows 使用相同 CMake 入口并选择固定 MSVC／Qt 工具链，构建和测试目录应放在专用
工作区内。测试数据、模拟旧配置、`paths.json` 回执及测试临时目录均位于构建目录的
`test-data/` 下。测试不会写入真实用户注册表来制造“旧配置”。

独立套件验证双 scope 配置文件路径、无正式设置继承、模拟旧文件字节不变、真实
WidgetTuner 早期读取、真实 UrlFetcher 对本地 HTTP 响应的磁盘缓存、默认路径兼容及
无效路径拒绝。Linux 包含不可写目录和符号链接；Windows 增加原生 junction 测试，
无符号链接权限时该用例会报告 skipped，不能算作验证通过。目录不可写的 Windows ACL
用例同样明确 skipped；只读 INI 用例仍执行。

完整原生构建还运行 `AppProfile.RuntimeServices`：真实录制 MCAP、源缓存发布、
中文空格路径下的真实随包插件同步／加载／回执、市场默认仓库／锁、插件宿主设置及
启用 3D 时的 URDF 临时解包。这个集成项不会在
Qt-only 构建中伪造通过。完整主程序、Windows 实机及安装器验收仍须分别记录具体
提交与产物；仅有上述单元测试不能替代它们。
