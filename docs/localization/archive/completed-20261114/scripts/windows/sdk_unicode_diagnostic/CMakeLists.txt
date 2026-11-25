cmake_minimum_required(VERSION 3.28)
project(SdkUnicodeDiagnostic LANGUAGES CXX)
set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)
# Explicit local source/header inputs only. No download, SDK pin change or Qt.
foreach(var SDK_SOURCE FMT_INCLUDE JSON_INCLUDE)
  if(NOT IS_DIRECTORY "${${var}}")
    message(FATAL_ERROR "Required local directory: ${var}")
  endif()
endforeach()
add_executable(sdk_unicode_probe probe.cpp
  "${SDK_SOURCE}/pj_plugins/src/plugin_catalog.cpp"
  "${SDK_SOURCE}/pj_plugins/src/detail/vtable_validation.cpp"
  "${SDK_SOURCE}/pj_base/src/semver.cpp")
target_compile_features(sdk_unicode_probe PRIVATE cxx_std_20)
target_compile_definitions(sdk_unicode_probe PRIVATE FMT_HEADER_ONLY)
target_include_directories(sdk_unicode_probe PRIVATE "${FMT_INCLUDE}" "${JSON_INCLUDE}"
  "${SDK_SOURCE}/pj_base/include" "${SDK_SOURCE}/pj_plugins/include"
  "${SDK_SOURCE}/pj_plugins/dialog_protocol/include" "${SDK_SOURCE}/pj_plugins/widget_protocol/include")
if(MSVC)
  target_compile_options(sdk_unicode_probe PRIVATE /utf-8 /W4)
endif()
target_link_libraries(sdk_unicode_probe PRIVATE ${CMAKE_DL_LIBS})
