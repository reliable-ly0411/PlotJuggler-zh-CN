# 3.x 接收方重链接材料：实施方案（未闭合）

本方案是发布准备，**不是已经提供源码或重链接材料的声明**。每个发布制品及配置必须有独立材料、输入清单和接收方验证；制品改变时重新绑定。下述对象导出是可选工程路径，不能把它作为唯一方案；另见文末完整源码重建路径。不要在未完成全部步骤时把它包装成最终许可说明。

## Linux x86-64 已有构建事实

rc.12 源码提交 `f4d777a14e08fc2be17e68ebc43a88fa73ad1357` 的 ON 和 OFF 是两个独立 Unix Makefiles 构建，各自 `plotjuggler_app/CMakeFiles/plotjuggler.dir/link.txt` 是实际 CMake 链接命令，链接目录是对应构建树的 `plotjuggler_app`。各自命令包括应用对象、资源对象、backward 对象、`libplotjuggler_base.a`、`libcolorwidgets.a`、`libqt_advanced_docking.a`、Qwt 等静态库、Wasmer 静态库、Qt 等共享库以及 `-lpthread -ldl -lm -lxcb`；驱动器还有隐式启动文件和运行库。ON 明确包含本地图像资源对象，OFF 不包含。

只读盘点：ON 79、OFF 78 个显式对象/库均存在；字节总量分别约 266.6 MB 和 218.5 MB。两个构建的 `3rdparty/backward-cpp/CMakeFiles/backward_object.dir/backward_object_autogen/mocs_compilation.cpp.o` 与同目录 `backward.cpp.o` 均含私有目录原始字符串，不能直接公开。这个初筛未覆盖所有隐私规则，也不证明其他文件干净。构建使用 Ubuntu GCC 13.3.0 和 GNU ld 2.42；`libm.so`、`libgcc_s.so` 是进一步引用其他库的链接脚本，`-l` 不能当成已归档输入。原构建 ON/OFF 程序 SHA256 分别为 `b5b09adebfd5ad26bcc5aa2c1b6231cb994817a50d3411d3b20107893437204e`、`f37eeb690b695685b4b0ad0fb84a0f4394658ae2f9e181fc12a71e97a8fd7a72`；它们不是后续候选的哈希。

## 可选路径：下一次集中构建及对象导出

1. 保留目标配置对应的源码完整提交和依赖锁，将源树与构建目录置于明确登记的私有根；为应用及 backward 目标的 C/C++ 选项设置源、构建、依赖根的 `-ffile-prefix-map`/`-fdebug-prefix-map`，检查生成的 moc 源及其记录是否还含原路径。必要时也要修正生成器路径；不能假设编译器选项会改写所有生成源中的字符串。重新构建受影响对象与链接，产物按新候选重新封存。运行对象和最终文件的原始隐私审计，包括所有登记私有根、UTF-8/UTF-16、密钥和 token；不得修改二进制字节来掩盖命中。
2. 以本次候选二进制 SHA、完整源码 commit、构建配置、平台架构和工具链身份建立独立导出目录。把链接命令中的每个显式对象、静态库、共享库复制到不可冲突的相对路径，保存 SHA256、长度、角色、对应原始链接参数次序。拒绝不存在或变化的输入、路径逃逸、符号链接指向未知位置、未识别的命令参数或响应文件；导出前后哈希应一致。把 rpath 等私有路径替换成经过验证的接收方相对运行路径，不能发布原始绝对命令。
3. 使用实际驱动器和链接器跟踪原命令，枚举 `-l`、链接脚本展开、启动文件、编译器隐式库及搜索目录，并记录对应文件哈希和工具链版本。将可再分发所需材料一起提供，或明确提供可复现获得的准确工具链、包版本及其校验方法；在干净环境验证而不是继承原构建目录。任何未知、未解决或变化的输入使导出失败；不得以源码 URL 或仅 `-l` 名称假装完成。为替换后的库保留明确输入位置，将参数顺序与其余选项原样映射成可执行命令。
4. 同一交付还需要完整对应源码包（含修改、许可证及构建/安装控制脚本），并列出 Conan 锁定 22 条的完整引用、公开 recipe 和实际来源材料、CPM 归档及摘要。逐个确认与二进制相符；锁文件和链接清单并不替代内容或通知。所需系统包、Qt、Wasmer 等材料及各自许可证另逐项核对。输出 `manifest.json`，对每个文件记相对路径、长度、SHA256，绑定制品、源码和工具链；对自身之外的清单做规范化摘要。公开前用同一隐私规则扫描实际待交付文件，包括对象、归档、命令及说明。
5. 将导出的目录移动到不含原构建树和私有依赖路径的隔离环境；核验所有摘要后，执行所提供的原版重链接命令并运行。再分别修改、编译 color_widgets 和 Qt Advanced Docking，替换对应库并重链接运行，观察修改生效，记录命令、退出码、实际文件哈希、运行结果和限制。只有该候选的真实材料、依赖获得方式和运行均核验后，才能考虑相应许可义务是否闭合。

## Windows 待收集的精确证据

现有 rc.12 主机记录包含 ON seal 和 ON 构建日志摘要，不包含实际 MSBuild 链接命令或对象目录；随后 OFF 配置复用了同一 build 路径。不能把现存 OFF 对象当作 ON 对象，亦不能根据 CMake 猜测 Windows 链接命令。需要只读枚举实际 build 下 `plotjuggler_app/plotjuggler.vcxproj`、`plotjuggler_app/plotjuggler.dir/Release` 中 link command/write tlog、响应文件和对象，以及 `3rdparty/color_widgets`、`3rdparty/Qt-Advanced-Docking` 的 Release 静态库，核对每项存在、大小、SHA、时间与 build 日志；具体布局应以实际工程为准。还需查 APP 任务目录 `ON-build.stdout.log` 是否包含具体 linker 命令及响应文件。核对其阶段归属并将结果绑定 ON seal 后，才可设计 Visual Studio/Windows SDK、MSVC 默认库、资源和 response 文件的完整接收方材料。主机摘要中不要发布私有路径或敏感值。

若无法证明原对象对应所封存的 ON EXE，应在下一候选构建时先于改配置和清理封存完整链接材料，再核验最终产物，不能倒推。当前不声称 Windows 材料已导出、可重链接或许可已闭合。


## 可选路径：完整应用源码及修改库重建

许可原文支持对这条路径进行实际核查：`3rdparty/color_widgets/COPYING` 的 LGPL 3 对 Corresponding Application Code 定义包括对象和/或源码、所需数据及工具；第 4 节列出提供该代码以重组合的方式。`3rdparty/Qt-Advanced-Docking/LICENSE` 的 LGPL 2.1 第 6(a) 节亦列出使用该库的作品的对象和/或源码，目标是让接收方修改库并重链接。还需逐项核对通知、条款及其他依赖；以上是工程方案，不是许可结论。此路径不以交付编译对象或全部系统工具链隐式对象为前提，但必须证明提供的源码、数据、依赖和实际说明足以让接收方重建并运行修改版。

rc.12 已有源归档 SHA256 `40d630fdea4ec65fe4cd0e85defb463e96278e82a2a143428fa3e5fae22697fd`，对固定提交 `f4d777a14e08fc2be17e68ebc43a88fa73ad1357` 逐 blob 校验 1729 个受跟踪文件，无缺失或多余；它不包含下载依赖，也不能代表新的候选提交。当前两库目录中的 94 个文件均受 Git 跟踪：color_widgets 的 CMake 列出源及头，QtADS 的 CMake 列出源、头及 `ads.qrc`，AUTOMOC/AUTORCC 开启；两库共 24 个 qrc 引用均存在且受跟踪，均没有 `.ui` 文件。对整个工作树的 7 个受跟踪 qrc，463 个引用均存在且受跟踪，另有 50 个受跟踪 `.ui` 输入。此检查证明引用文件存在，不证明构建工具、生成步骤及其他外部依赖齐全；必须对最终候选重新检查。注意无 `.git` 的源归档会使 `cmake/ForkVersion.cmake` 使用 `gsource` 回退，完整 Git 包或明示这一差异并验证构建，不应把归档重建的版本标识冒充原制品。

按实际候选至少准备并验证：

1. 完整候选源码包、完整 commit/tree ID、归档 SHA256、提取后逐文件清单及许可证；包含应用、两库、DataFlash、所有 `.ui`/`.qrc` 引用、生成控制脚本、CMake 与锁/overlay。最终包还需提供实际可获取的材料与说明，不以尚未公开的 Git URL 当成可用副本。
2. Windows：`cmake/conan/windows-msvc194.lock` 的 recipe revisions 和 build requirements、对应的 `conanfile.txt`、自定义 OpenSSL overlay/配置、实际图中每个 host/build 的版本与 package ID、Conan/编译器/SDK/CMake/Ninja 或 MSBuild 版本及命令；实际选中的公共 recipe 和源归档、patches 要可获得并校验。锁并不包含完整源码。rc.12 已记录 data_tamer 1.0.3、Lua 5.4.7、nlohmann_json 3.12.0 和 Wasmer 7.0.1 的 Windows CPM 归档哈希及提取清单；Wasmer 包是二进制 SDK，不能冒充完整源码。非 Wasmer 的 CMake 下载地址为 tag 引用，未在这些调用中直接固定 URL_HASH，因此应由候选材料清单校验具体归档 SHA 并确认实际构建用的是这些字节；将其对应源码与适用通知另行提供或验证可获取性。
3. Linux：记录实际各包/源码版本、发行版、架构、Qt 开发包、编译器、CMake、Lua、Arrow/Parquet、Wasmer 和其他解析到的输入及配置，不能把 Windows Conan 记录或构建主机的缓存当成接收方材料。离线及在线获得方式的可用性按选定方案实测。发行包其他平台亦应各自盘点，而不是以 Linux 结果代表七包。
4. Qt：逐个核对最终分发的 Qt DLL/ELF、版本、模块、二进制来源、配置与对应源码（含分发者修改和构建/安装脚本）；Windows 5.15.2 可先将 `https://download.qt.io/archive/qt/5.15/5.15.2/` 作为待核官方源目录候选，由发布负责人验证准确模块源包、摘要和可获取性，不能仅根据目录名断言一致。Ubuntu 22.04 特定 QtCore backport 使用 `5.15.3+dfsg-2ubuntu0.2`：`scripts/build_qt5_core_backport.sh` 固定上游 orig、Ubuntu debian 源档摘要，先应用发行版 patches，再应用仓库内 `qtbug-92188.patch` 和 `qtbug-102484.patch`；应将两源档、两补丁、`SHA256SUMS`、脚本、配置、许可证与最终实际 QtCore 绑定提供并实测。该 backport 不等于 rc.12 本机 Ubuntu 24.04 的 Qt 5.15.13 或 Windows Qt 5.15.2，不得跨平台替代。

### 面向当前候选的最小实测

在最终候选源码封存后、原构建树以外的全新目录，从拟交付源码包解压，核验 commit/tree 和所有材料摘要；通过记录的工具链与精确输入完成原版构建，验证实际功能、配置和候选的关联。保留所有命令、退出码、输出哈希及获取记录；逐字节复现并非预设要求，但需要证明对应源码和构建配置。然后从相同源码包另建隔离副本，对 `3rdparty/color_widgets/src/color_palette.cpp` 和 `3rdparty/Qt-Advanced-Docking/src/ads_globals.cpp` 分别增加仅限验证的可观察标记或等价改动，完整重编对应库并重新链接应用，执行并证明两个改动都被加载；记录各输入及可观察结果。可结合 GUI 或隔离的启动测试，但不能让 `--version` 的单次结果冒充完整产品验收。不能修改发行二进制、也不能把 rc.11 使用原构建目录的实验冒充此接收方实测。若任一依赖无法取得、实际配置不明、标记未出现或平台无法运行，状态保持 incomplete。许可证闭合仍需按实际发行包逐项复核。
