# SPDX-License-Identifier: MPL-2.0
find_package(Qt6 REQUIRED COMPONENTS Widgets Svg Network Test)
get_filename_component(root "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
add_executable(localized_update_test
    localized_update_test.cpp
    "${root}/pj_runtime/src/UpdateChecker.cpp"
    "${root}/pj_runtime/include/pj_runtime/UpdateChecker.h"
    "${root}/pj_runtime/src/HttpGet.cpp")
set_target_properties(localized_update_test PROPERTIES AUTOMOC ON)
target_include_directories(localized_update_test PRIVATE "${root}/pj_runtime/include")
target_link_libraries(localized_update_test PRIVATE Qt6::Core Qt6::Network Qt6::Test)
target_compile_options(localized_update_test PRIVATE ${PJ_WARNING_FLAGS})
add_test(NAME LocalizedUpdateTest COMMAND localized_update_test)
# Reuse production resource generation, including in the standalone harness.
if(NOT TARGET pj_resources)
    add_subdirectory("${root}/resources" "${CMAKE_CURRENT_BINARY_DIR}/resources")
endif()
add_executable(localized_splash_test
    localized_splash_test.cpp
    "${root}/pj_app/src/Splashscreen.cpp"
    "${root}/pj_widgets/src/FrameworkTokens.cpp")
set_target_properties(localized_splash_test PROPERTIES AUTOMOC ON AUTORCC ON)
target_include_directories(localized_splash_test PRIVATE "${root}/pj_widgets/include")
target_link_libraries(localized_splash_test PRIVATE pj_app_language Qt6::Widgets Qt6::Svg Qt6::Test pj_resources)
target_compile_options(localized_splash_test PRIVATE ${PJ_WARNING_FLAGS})
if(MSVC)
    target_compile_options(localized_update_test PRIVATE /utf-8)
    target_compile_options(localized_splash_test PRIVATE /utf-8)
endif()
add_test(NAME LocalizedSplashTest COMMAND localized_splash_test)
set_tests_properties(LocalizedSplashTest PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")

add_executable(localized_original_meme_test ../localized_original_meme_test.cpp)
set_target_properties(localized_original_meme_test PROPERTIES AUTOMOC ON)
target_link_libraries(localized_original_meme_test PRIVATE Qt6::Gui Qt6::Test pj_resources)
target_compile_options(localized_original_meme_test PRIVATE ${PJ_WARNING_FLAGS})
if(MSVC)
    target_compile_options(localized_original_meme_test PRIVATE /utf-8)
endif()
add_test(NAME LocalizedOriginalMemeTest COMMAND localized_original_meme_test)
set_tests_properties(LocalizedOriginalMemeTest PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
