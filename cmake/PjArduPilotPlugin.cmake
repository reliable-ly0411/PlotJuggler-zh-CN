# SPDX-License-Identifier: MPL-2.0
# The LGPL loader remains a replaceable DSO from its independently maintained
# repository. The enclosing Git tree pins the submodule commit; no fetch or
# moving branch is consulted by CMake or by the application at runtime.
include_guard(GLOBAL)

if(EMSCRIPTEN)
    set(_pj_apbin_default OFF)
else()
    set(_pj_apbin_default ON)
endif()
option(PJ_BUILD_ARDUPILOT_PLUGIN "Build the pinned native ArduPilot DataFlash plugin" ${_pj_apbin_default})
unset(_pj_apbin_default)
if(NOT PJ_BUILD_ARDUPILOT_PLUGIN)
    return()
endif()
if(EMSCRIPTEN)
    message(FATAL_ERROR "PJ_BUILD_ARDUPILOT_PLUGIN requires a native shared-library platform")
endif()

set(_pj_apbin_dir "${CMAKE_CURRENT_LIST_DIR}/../3rdparty/plotjuggler-apbin-plugins")
if(NOT EXISTS "${_pj_apbin_dir}/sdk4/CMakeLists.txt")
    message(FATAL_ERROR
        "The pinned ArduPilot SDK4 submodule is missing. Run "
        "'git submodule update --init --recursive', or explicitly disable "
        "PJ_BUILD_ARDUPILOT_PLUGIN for a build without BIN support.")
endif()

set(APBIN_BUILD_PLUGIN ON CACHE BOOL "Build the independent ArduPilot DSO" FORCE)
set(APBIN_BUILD_TESTS ${PJ_BUILD_TESTS} CACHE BOOL "Build ArduPilot parser and ABI regressions" FORCE)
set(APBIN_PLUGIN_INSTALL_DIRECTORY "lib/plotjuggler/plugins/ardupilot-dataflash" CACHE STRING "" FORCE)
if(TARGET pj_app)
    # Match ExtensionCatalogService's bundledPluginsDir() in both single- and
    # multi-config build layouts, without adding a second discovery mechanism.
    set(APBIN_PLUGIN_OUTPUT_DIRECTORY
        "$<TARGET_FILE_DIR:pj_app>/../lib/plotjuggler/plugins/ardupilot-dataflash" CACHE PATH "" FORCE)
else()
    set(APBIN_PLUGIN_OUTPUT_DIRECTORY "" CACHE PATH "" FORCE)
endif()
add_subdirectory("${_pj_apbin_dir}/sdk4" "${CMAKE_BINARY_DIR}/ardupilot-dataflash")
file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/ardupilot-package-path-$<CONFIG>.txt"
    CONTENT "$<TARGET_FILE:ardupilot_source_plugin>\n")
if(TARGET pj_app)
    add_dependencies(pj_app ardupilot_source_plugin)
endif()
if(PJ_BUILD_TESTS AND TARGET pj_app_loader_testlib)
    add_executable(ardupilot_import_test "${CMAKE_SOURCE_DIR}/pj_app/tests/ardupilot_import_test.cpp")
    target_link_libraries(ardupilot_import_test PRIVATE pj_app_loader_testlib pj_app_language)
    target_compile_definitions(ardupilot_import_test PRIVATE
        PJ_ARDUPILOT_PLUGIN_PATH="$<TARGET_FILE:ardupilot_source_plugin>"
        PJ_ARDUPILOT_FIXTURES="${_pj_apbin_dir}/sdk4/tests"
        PJ_ARDUPILOT_REAL_LOG="${_pj_apbin_dir}/tests/logs/00000001.BIN")
    add_dependencies(ardupilot_import_test ardupilot_source_plugin)
    target_compile_options(ardupilot_import_test PRIVATE ${PJ_WARNING_FLAGS})
    add_test(NAME ArduPilotFileLoaderTest COMMAND ardupilot_import_test)
    set_tests_properties(ArduPilotFileLoaderTest PROPERTIES TIMEOUT 90)
    # pj_app's interpreter lookup is directory-scoped; resolve the host tool
    # here too, rather than silently omitting this full-application regression.
    find_package(Python3 REQUIRED MODULE COMPONENTS Interpreter)
    if(Python3_Interpreter_FOUND AND TARGET pj_app)
        add_test(NAME ArduPilotLayoutRestoreTest
            COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/tests/check_ardupilot_layout.py"
                --app "$<TARGET_FILE:pj_app>"
                --plugins "$<TARGET_FILE_DIR:ardupilot_source_plugin>"
                --real-bin "${_pj_apbin_dir}/tests/logs/00000001.BIN")
        set_tests_properties(ArduPilotLayoutRestoreTest PROPERTIES TIMEOUT 180)
    endif()
endif()
unset(_pj_apbin_dir)
