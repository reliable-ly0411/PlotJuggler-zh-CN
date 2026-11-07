# PlotJuggler 中文版 · 非官方 4.x 分支

基于 [PlotJuggler 官方项目](https://github.com/PlotJuggler/PlotJuggler)的非官方中文分支，
用于时序信号、飞控日志及多模态数据的交互式分析。保留上游英文界面，新增中文界面和
独立的 ArduPilot DataFlash BIN 加载插件。

- **下载已发布中文版：** [v4.0.0-zh.1.rc.4](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/v4.0.0-zh.1.rc.4)，
  提供 Windows x64 安装器、Linux x86_64 AppImage 和 amd64 DEB。
  此版本为预发布候选，支持简体中文与 English，使用 Qt 6.11.1。
- **开发线：** `zh-CN-4.x-dev` 当前为 `4.1.0-zh.1.dev.1`，使用 Qt 6.12.0，
  包含简体中文、繁體中文（台灣）与 English。开发源码尚未发布为新的已验安装包，繁中不在 rc.4 中。
- **稳定维护线：** `zh-CN-4.x` 是默认分支；“稳定线”指分支用途，不改变 rc.4 的预发布状态。
  `main-4.x` 仅镜像上游，3.x 的 `zh-CN` / `zh-CN-dev` 独立维护。

新配置默认简体中文，可在首选项切换语言，下次启动生效。界面语言不改变数值或数据解析规则。
详细覆盖和限制见[中文与多语言说明](docs/localization/README.zh-CN.md)。

This is an unofficial Chinese-language fork of PlotJuggler. Published rc.4 packages support
Simplified Chinese and English; Traditional Chinese (Taiwan) is available in the unpublished
development line. For Chinese packages, use the fork release linked above, not the upstream downloads.

## 上游功能概览 / Upstream capabilities

以下保留上游的功能介绍与示例。部分格式、流和工具需要单独安装兼容插件或配置外部环境；
不表示所有功能都已随本分支的安装包提供或完成验证。截图展示上游工作区，不是中文版验收截图。

![](docs/plotjuggler_banner.svg)


PlotJuggler 4 is an extensible, performant and open-source multi-modal visualization platform.

Explore recorded or live data, compare test runs, and analyze and transform your data,
in a single application.

<!-- Original screenshots: https://plotjuggler.io/videos/pj-scene3D-800.jpg,
     https://plotjuggler.io/videos/pj-plotting-800.jpg,
     https://plotjuggler.io/videos/pj-waymo-800.jpg. -->

![Robot model, camera feeds, depth images and joint torque plots in a shared PJ4 workspace](docs/images/workspace.jpg)

## Analyze signals interactively

- **Drag and drop your data.** Drag signals into time-series and XY plots, zoom into events, and inspect individual samples.
- **Validate changes across runs.** Load several recordings, align their timelines, and overlay signals to compare behavior.
- **Analyze the signal.** Filter noise, measure rates of change, integrate values, or inspect frequency content with Fast Fourier Transforms.
- **Add your own functions.** Create derived series with custom transforms in Lua and Python, alongside the built-in filters.
- **Reuse your analysis.** Arrange plots in tabs and dockable panels, then save your layout and transforms for the next investigation.

## Multimodal data, synchronized in time

Efficient data storage, GPU-accelerated rendering and on-demand media decoding
help keep large recordings responsive as you explore.

<table>
  <tr>
    <td valign="top">
      <h3>Images and Videos</h3>
      <ul>
        <li>Raw and encoded images</li>
        <li>H.264, H.265 or AV1 video</li>
        <li>Live video streaming through WebRTC</li>
        <li>2D annotations and markers</li>
      </ul>
    </td>
    <td valign="top">
      <h3>3D rendering</h3>
      <ul>
        <li>Pointcloud, including compressed</li>
        <li>Meshes and URDF robot models</li>
        <li>Occupancy grids and maps (2D)</li>
        <li>Elevation grid maps (2.5D)</li>
        <li>3D annotations, trajectories and markers</li>
      </ul>
    </td>
  </tr>
</table>

## Work with the data you already have

Open supported formats directly and connect to your existing sensor and messaging
systems. Install ready-to-use loaders, streamers and tools through
**File → Marketplace**:

| Sources | Formats |
| --- | --- |
| **Files** | CSV, MCAP, Parquet, PX4 ULog, LeRobot, MP4, PCD and PLY |
| **Live streams** | ROS 2, MQTT, ZeroMQ, UDP, WebSocket bridges, WebRTC and Lab Streaming Layer |
| **Message encodings** | ROS 1/2, Protobuf, JSON, CBOR, BSON, Apache Arrow and MessagePack |
| **Cloud storage** | [Mosaico](https://mosaico.dev/) |

Need a custom integration? Build a loader, streamer, parser or toolbox with the
[plugin SDK](https://github.com/PlotJuggler/plotjuggler_sdk), or start from the
[official plugins](https://github.com/PlotJuggler/pj-official-plugins).

## 下载与安装中文版

请打开 [rc.4 中文版发布页](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases/tag/v4.0.0-zh.1.rc.4)，
阅读已知限制并核对同页的 `SHA256SUMS.txt`。完整历史见[本仓库 Releases](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/releases)。
预发布候选不会通过 GitHub 的 `releases/latest` 自动选中。

| 系统 | rc.4 下载文件 | 安装方式 |
| --- | --- | --- |
| Windows x64 | `PlotJuggler-4.0.0-zh.1.rc.4-Windows-x64-zh-CN.exe` | 运行离线安装器，建议使用独立目录；安装器未签名 |
| Linux x86_64 | `PlotJuggler-4.0.0-zh.1.rc.4-x86_64-zh-CN.AppImage` | 赋予执行权限后运行 |
| Ubuntu / Debian amd64 | `plotjuggler4_4.0.0.zh.1.rc.4-1_amd64-zh-CN.deb` | 用 `sudo apt install ./下载的文件名.deb` 安装，运行 `plotjuggler4` |

Linux 包的实际验收环境为 Ubuntu 22.04 / 24.04，普通组件要求 glibc 2.35 或更新版本；
不据此承诺所有 Linux 发行版。AppImage 缺少 FUSE 时可用 `APPIMAGE_EXTRACT_AND_RUN=1` 运行。
DEB 文件名使用点号，包内版本仍为 `4.0.0~zh.1~rc.4-1`。
没有本中文版的 APT 或 IFW 自动更新服务，更新请使用本仓库发布页。

升级前备份布局和配置。测试开发版时可使用[独立配置目录](docs/localization/ISOLATED_PROFILE.zh-CN.md)，
避免混用市场插件和设置。市场更新可能覆盖随包的插件修复或汉化版本。

### ArduPilot DataFlash 日志

原生中文版包包含独立的 [ArduPilot BIN 插件](https://github.com/reliable-ly0411/plotjuggler-apbin-plugins)，
可加载 DataFlash `.BIN` 日志并绘制数值字段；在加载数据后将所需信号拖到绘图区域。
插件版本、固定来源和与上游的差异见[插件说明](docs/localization/README.zh-CN.md#ardupilot-bin-插件)。
插件与宿主分别维护，Qt5 / PlotJuggler 3 插件不能直接用于 PlotJuggler 4。

### 覆盖与兼容性限制

- 翻译覆盖主程序及限定的插件显示内容，不保证任意第三方插件、系统界面或图片文字均已翻译。
- rc.4 的 Linux 包包含 21 个插件，Windows 包含 19 个；市场可用项目不等于随包项目。
  Linux 的 ROS 2 订阅插件需要外部 ROS 环境，不能用普通包验收推断其功能已验证。
- 未提供已验的 macOS、ARM 或 WebAssembly 中文发布包。WebAssembly 不启用原生 BIN 共享插件。
- 不保证完全兼容 3.x 布局。开发线的源码测试不能替代完整应用、图形界面及最终安装包验收。

### 官方英文发行版与 APT

若需要官方发行版，请使用 [PlotJuggler 官方安装说明](https://github.com/PlotJuggler/PlotJuggler#how-to-get-started)。
`apt.plotjuggler.io` 属于官方更新渠道，不是本仓库的中文安装源。

### 源码构建与贡献

先确认要构建的标签或分支，再阅读[构建指南](docs/BUILDING.md)及
[本分支构建与回归说明](docs/localization/README.zh-CN.md#构建与回归)。
GitHub 自动生成的源码 ZIP/TAR 不含子模块；构建时需递归初始化子模块。
版本和工具链以所检出源码的 [versions.env](versions.env) 为准。

问题反馈请附版本、操作系统、复现步骤及可公开的最小样例，提交到
[本分支 Issues](https://github.com/reliable-ly0411/PlotJuggler-zh-CN/issues)。
不要上传含私人信息的飞控日志。开发流程见[分支规范](docs/BRANCHING.zh-CN.md)与
[发布规范](RELEASING.md)；草稿 PR 不代表已合并或已发布功能。

## License

The desktop application is released under the [Mozilla Public License 2.0](LICENSE).
The upstream WebAssembly bundle has separate GPL-3.0 distribution requirements; see
[WebAssembly deployment](docs/WASM_DEPLOYMENT.md).
Third-party dependencies retain their own licenses. PlotJuggler and its original capabilities
are developed by the [upstream project and contributors](https://github.com/PlotJuggler/PlotJuggler).
The ArduPilot DataFlash loader derives from
[ArduPilot/plotjuggler-apbin-plugins](https://github.com/ArduPilot/plotjuggler-apbin-plugins)
and retains LGPL-3.0-only as a separate shared plugin. The SDK and bundled components
retain their respective licenses; see the package license notices for distribution details.
