# SPDX-License-Identifier: MPL-2.0
find_package(Qt6 REQUIRED COMPONENTS Network Test)
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
if(MSVC)
    target_compile_options(localized_update_test PRIVATE /utf-8)
endif()
