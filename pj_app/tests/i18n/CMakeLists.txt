# SPDX-License-Identifier: MPL-2.0
cmake_minimum_required(VERSION 3.22)
project(plotjuggler4_i18n_tests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Exercise the production language loader and embedded catalog with only the
# pinned Qt kit; useful before bootstrapping the full application's SDK graph.
include("${CMAKE_CURRENT_LIST_DIR}/../../../cmake/PjVersions.cmake")
pj_read_versions("${CMAKE_CURRENT_LIST_DIR}/../../../versions.env")
find_package(Qt6 ${PJ_QT_VERSION} REQUIRED COMPONENTS Core Test LinguistTools)
if(MSVC)
    set(PJ_WARNING_FLAGS /W4 /WX /permissive-)
else()
    set(PJ_WARNING_FLAGS -Wall -Wextra -Wshadow -Wconversion -Wpedantic -Werror)
endif()
enable_testing()
include("${CMAKE_CURRENT_LIST_DIR}/../../cmake/PjAppLanguage.cmake")
pj_add_app_language()
pj_add_app_language_test()

if(NOT CMAKE_CROSSCOMPILING AND TARGET Qt6::qmake)
    add_test(NAME QtTranslationPaths
        COMMAND "${CMAKE_COMMAND}"
            "-DTEST_BINARY_DIR=${CMAKE_CURRENT_BINARY_DIR}/translation-path-tests"
            "-DQT_QMAKE=$<TARGET_FILE:Qt6::qmake>"
            "-DQT_CONFIG_DIR=${Qt6_DIR}"
            "-DTEST_GENERATOR=${CMAKE_GENERATOR}"
            "-DLANGUAGE_CMAKE=${CMAKE_CURRENT_LIST_DIR}/../../cmake/PjAppLanguage.cmake"
            -P "${CMAKE_CURRENT_LIST_DIR}/check_translation_paths.cmake")
    set_tests_properties(QtTranslationPaths PROPERTIES TIMEOUT 180)
endif()

find_package(Qt6 REQUIRED COMPONENTS Widgets Xml UiTools)
add_executable(qt_file_dialog_language_test ../qt_file_dialog_language_test.cpp)
set_target_properties(qt_file_dialog_language_test PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE)
target_link_libraries(qt_file_dialog_language_test PRIVATE pj_app_language Qt6::Widgets Qt6::Test)
target_compile_options(qt_file_dialog_language_test PRIVATE ${PJ_WARNING_FLAGS})
if(MSVC)
    target_compile_options(qt_file_dialog_language_test PRIVATE /utf-8)
endif()
add_test(NAME QtFileDialogLanguageTest COMMAND qt_file_dialog_language_test)
set_tests_properties(QtFileDialogLanguageTest PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")

