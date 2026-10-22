# SPDX-License-Identifier: MPL-2.0
cmake_minimum_required(VERSION 3.22)
project(pj_file_dialog_preflight LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC_SEARCH_PATHS "${CMAKE_CURRENT_LIST_DIR}/../../src")
include("${CMAKE_CURRENT_LIST_DIR}/../../../cmake/PjVersions.cmake")
pj_read_versions("${CMAKE_CURRENT_LIST_DIR}/../../../versions.env")
find_package(Qt6 ${PJ_QT_VERSION} REQUIRED COMPONENTS Core Gui Widgets Svg Test)
add_executable(file_dialog_preflight
  file_dialog_preflight.cpp ../../../resources/resources.qrc
  ../../src/FileDialog.cpp ../../src/Dialog.cpp ../../src/Dialog.ui
  ../../src/FrameworkTokens.cpp ../../src/SideDrawer.cpp ../../src/Scrollbar.cpp
  ../../include/pj_widgets/FileDialog.h ../../include/pj_widgets/Dialog.h
  ../../include/pj_widgets/Scrollbar.h)
target_include_directories(file_dialog_preflight PRIVATE ../../include)
target_link_libraries(file_dialog_preflight PRIVATE Qt6::Core Qt6::Gui Qt6::Widgets Qt6::Svg Qt6::Test)
set_target_properties(file_dialog_preflight PROPERTIES WIN32_EXECUTABLE FALSE)
if(MSVC)
  target_compile_options(file_dialog_preflight PRIVATE /utf-8)
endif()
enable_testing()
add_test(NAME FileDialogPreflight COMMAND file_dialog_preflight -o -,txt -o "${CMAKE_BINARY_DIR}/file-dialog.txt,txt")
set_tests_properties(FileDialogPreflight PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
