# Windows Conan 构建路径映射

graph 和 install 均显式使用 `cmake/conan/windows-msvc194.lock`，把已验证图的 host 与 build recipe 修订用于解析，
而非在取回远端最新修订后才拒绝。该文件与 rc.10 本地原生验证实际使用的 lockfile 字节一致，
SHA256 为 `b987509519ea184d4326ae2d618260b0f950b94a72ed810ea9087909960b0d34`。

`windows_conan_pathmap.py` 默认将源码根和独立 Conan 缓存根映射到 `Z:/pj-source` 和 `Z:/pj-conan`。两个根必须使用编译器实际看到的绝对路径、互不嵌套；源码、生成源与 build 目录放在同一 workspace 内即可被源码根覆盖。外置 build 或其他外置生成源目录需要额外映射及原生探针，本方案不覆盖这些路径。提供 `--base-profile <文件>` 可使用本地明确的 host profile；省略时需先准备 Conan 的 default profile。

本机 MSVC 19.44 的两个独立路径 C/C++ 探针中，正斜杠映射在两种顺序均生效，原反斜杠输入分别映射到正斜杠逻辑前缀并保留原后缀。固定 OpenSSL 3.6.5 recipe 在 Perl 双引号内使用 flags，正斜杠可避免反斜杠转义破坏；这两项探针不能代替真实依赖编译命令及 DLL 的检查。

工作流为每次运行建立独立缓存，强制 `windows_conan_host_refs.json` 中 22 个 host 静态库按指定版本重建，并用 Conan JSON 在安装前后核对精确 recipe revision、package ID 存在和 `binary=Build`；host 编译依赖集合变化或得到 Cache/Download 等状态将失败。头文件包不是静态库，build-context 工具不纳入此计数。同名 protobuf/zlib 同时存在于 build context，因此它们也可能被对应模式重建，但 CMake、NASM、Perl 不会再被通配模式无条件重建。graph 和 install JSON 保存在 runner 临时目录作私有诊断，不作为公开制品直接上传。

Conan 2.34 的 [install 参考](https://docs.conan.io/2/reference/commands/install.html) 和 [graph info 参数](https://docs.conan.io/2/reference/commands/graph/info.html) 描述了可组合的 `--build=missing` 与包引用匹配强制重建；[JSON 格式参考](https://docs.conan.io/2/reference/commands/formatters/graph_info_json_formatter.html) 说明 install 的 graph 输出。固定 graph 来自已完成的 rc.10 本地离线图；更新依赖时必须重新审阅引用、revision 和构建证据，不能悄悄放宽核验。显式 `--build` 模式会增加构建成本，这是为避免取回已有二进制。

尚需在实际 Windows CI/本机构建中核对所有源码库的编译命令、映射前后 DLL 字符串、完整来源及许可证，之后仍须通过现有隐私和独立身份门禁；package ID 或 Build 状态本身不证明文件内容正确。22 个库的精确 recipes 中 Abseil、OpenSSL、Arrow 已审，其余尚未逐份审阅。
