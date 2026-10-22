# SPDX-License-Identifier: MPL-2.0
# IFW executes QJSEngine, whose special arguments binding differs from Node.
find_package(Qt6 REQUIRED COMPONENTS Core Qml)
add_executable(installer_script_test installer_script_test.cpp)
target_link_libraries(installer_script_test PRIVATE Qt6::Core Qt6::Qml)
target_compile_definitions(installer_script_test PRIVATE
    PJ_INSTALLER_SCRIPT_PATH="${CMAKE_CURRENT_LIST_DIR}/../../../packaging/installer/packages/io.plotjuggler.application/meta/installscript.qs")
if(MSVC)
    target_compile_options(installer_script_test PRIVATE /W4 /WX /permissive- /utf-8)
else()
    target_compile_options(installer_script_test PRIVATE -Wall -Wextra -Wshadow -Wconversion -Wpedantic -Werror)
endif()
set_target_properties(installer_script_test PROPERTIES WIN32_EXECUTABLE FALSE)
add_test(NAME InstallerScriptQtEngine COMMAND installer_script_test)
