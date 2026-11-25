# SPDX-License-Identifier: MPL-2.0
find_package(Qt6 REQUIRED COMPONENTS Xml)
if(NOT TARGET plotjuggler_qwt)
  add_subdirectory("${pj_root}/3rdparty/qwt" qwt)
endif()
add_executable(fft_live_test
  fft_live_test.cpp
  ../../src/bundled_translations.cpp
  ../../src/pj_ui_loader.cpp
  ../../src/chart_preview_widget.cpp
  ../../src/chart_placeholder_overlay.hpp
  ../../include/pj_plugins/host_qt/chart_preview_widget.hpp
  ../../../pj_plotting/widget/src/MarkerPainter.cpp)
set_target_properties(fft_live_test PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE)
target_include_directories(fft_live_test PRIVATE
  ../../include ../../src ../../../pj_plotting/widget/include)
target_link_libraries(fft_live_test PRIVATE
  pj_app_language pj_widgets pj_resources plotjuggler_qwt
  plotjuggler_sdk::plugin_host plotjuggler_sdk::plugin_sdk
  Qt6::UiTools Qt6::Xml Qt6::Test nlohmann_json::nlohmann_json)
target_compile_options(fft_live_test PRIVATE ${PJ_WARNING_FLAGS})
if(MSVC)
  target_compile_options(fft_live_test PRIVATE /utf-8)
endif()
target_compile_definitions(fft_live_test PRIVATE PJ_FFT_TEST_PLUGIN="${PJ_FFT_TEST_PLUGIN}")
add_test(NAME FftOfficialBinaryLanguageTest COMMAND fft_live_test)
set_tests_properties(FftOfficialBinaryLanguageTest PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
