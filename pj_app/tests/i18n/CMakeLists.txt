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

find_package(Qt6 REQUIRED COMPONENTS Widgets Xml)
add_executable(pj_bundled_translations_test
    ../../../pj_dialog_host/tests/bundled_translations_qtest.cpp
    ../../../pj_dialog_host/src/bundled_translations.cpp)
set_target_properties(pj_bundled_translations_test PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE)
target_include_directories(pj_bundled_translations_test PRIVATE ../../../pj_dialog_host/include)
target_link_libraries(pj_bundled_translations_test PRIVATE Qt6::Widgets Qt6::Xml Qt6::Test)
target_compile_options(pj_bundled_translations_test PRIVATE ${PJ_WARNING_FLAGS})
if(MSVC)
    target_compile_options(pj_bundled_translations_test PRIVATE /utf-8)
endif()
target_compile_definitions(pj_bundled_translations_test PRIVATE
    PJ_CSV_UI_FIXTURE="${CMAKE_CURRENT_LIST_DIR}/../../../pj_dialog_host/tests/fixtures/csv_1_0_7.ui")
add_test(NAME pj_bundled_translations_test COMMAND pj_bundled_translations_test
        -o -,txt -o "${CMAKE_BINARY_DIR}/Testing/Temporary/bundled-translations.txt,txt")
set_tests_properties(pj_bundled_translations_test PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
