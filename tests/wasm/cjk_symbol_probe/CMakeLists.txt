# SPDX-License-Identifier: MPL-2.0
cmake_minimum_required(VERSION 3.22)
project(pjGlyphProbe LANGUAGES CXX)
find_package(Qt6 6.12.0 EXACT REQUIRED COMPONENTS Widgets)
set(CMAKE_AUTORCC ON)
qt_add_executable(pjGlyphProbe main.cpp BundledFont.cpp primary.qrc NotoSansSC/wasm-cjk.qrc)
target_link_libraries(pjGlyphProbe PRIVATE Qt6::Widgets)
