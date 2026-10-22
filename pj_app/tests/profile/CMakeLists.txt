# SPDX-License-Identifier: MPL-2.0
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    cmake_minimum_required(VERSION 3.22)
    project(plotjuggler4_profile_tests LANGUAGES CXX)
    set(CMAKE_CXX_STANDARD 20)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
    set(CMAKE_CXX_EXTENSIONS OFF)
    include("${CMAKE_CURRENT_LIST_DIR}/../../../cmake/PjVersions.cmake")
    pj_read_versions("${CMAKE_CURRENT_LIST_DIR}/../../../versions.env")
    find_package(Qt6 ${PJ_QT_VERSION} REQUIRED COMPONENTS Core)
    enable_testing()
endif()

find_package(Qt6 REQUIRED COMPONENTS Widgets Network)
get_filename_component(profile_root "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
add_executable(app_profile_test
    app_profile_test.cpp
    "${profile_root}/pj_app/src/AppProfile.cpp"
    "${profile_root}/pj_app/src/WidgetTuner.cpp"
    "${profile_root}/pj_widgets/src/FrameworkTokens.cpp"
    "${profile_root}/pj_marketplace/src/core/PlatformUtils.cpp"
    "${profile_root}/pj_scene3D/widgets/src/url_fetcher.cpp")
set_target_properties(app_profile_test PROPERTIES AUTOMOC ON WIN32_EXECUTABLE FALSE)
target_include_directories(app_profile_test PRIVATE
    "${profile_root}/pj_app/src"
    "${profile_root}/pj_marketplace/include"
    "${profile_root}/pj_widgets/include"
    "${profile_root}/pj_scene3D/widgets/src"
    "${profile_root}/pj_scene3D/core/include")
target_link_libraries(app_profile_test PRIVATE Qt6::Widgets Qt6::Network)
target_compile_definitions(app_profile_test PRIVATE PJ_PROFILE_SOURCE_DIR="${profile_root}")
if(MSVC)
    target_compile_options(app_profile_test PRIVATE /W4 /WX /permissive- /utf-8)
else()
    target_compile_options(app_profile_test PRIVATE -Wall -Wextra -Wshadow -Wconversion -Wpedantic -Werror)
endif()

# Each case owns a fresh process: profile installation is deliberately immutable.
# Every created file stays below this build-tree directory, including failures.
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/test-data/tmp"
                    "${CMAKE_CURRENT_BINARY_DIR}/test-data/framework-cache")
set(profile_cases DefaultPaths IsolatedPaths EqualsSyntax EarlyWidgetSettings AtomicSettingsProbe
        InvalidArguments RootIsFile ChildIsFile UnwritableDirectory UnwritableSettings
        LinkedDirectory LinkedSettingsFile StartupOrder)
if(WIN32)
    list(APPEND profile_cases LinkedJunction)
endif()
foreach(profile_case IN LISTS profile_cases)
    add_test(NAME AppProfile.${profile_case}
        COMMAND app_profile_test "${profile_case}" "${CMAKE_CURRENT_BINARY_DIR}/test-data")
    set_tests_properties(AppProfile.${profile_case} PROPERTIES
        ENVIRONMENT "QT_QPA_PLATFORM=offscreen;TMP=${CMAKE_CURRENT_BINARY_DIR}/test-data/tmp;TEMP=${CMAKE_CURRENT_BINARY_DIR}/test-data/tmp;TMPDIR=${CMAKE_CURRENT_BINARY_DIR}/test-data/tmp;XDG_CACHE_HOME=${CMAKE_CURRENT_BINARY_DIR}/test-data/framework-cache"
        TIMEOUT 30 SKIP_RETURN_CODE 77)
endforeach()

# The full native build adds actual runtime/store/recording integration. The
# Qt-only harness above cannot claim these services merely from path arithmetic.
if(TARGET pj_runtime)
    add_executable(app_profile_services_test app_profile_services_test.cpp)
    target_link_libraries(app_profile_services_test PRIVATE pj_runtime Qt6::Core)
    target_compile_definitions(app_profile_services_test PRIVATE
        PJ_PROFILE_PLUGIN_PATH="$<TARGET_FILE:mock_data_source_v2_plugin>")
    add_dependencies(app_profile_services_test mock_data_source_v2_plugin)
    set_target_properties(app_profile_services_test PROPERTIES WIN32_EXECUTABLE FALSE)
    if(TARGET pj_scene3d_widgets)
        # This source directly includes GLM; a sibling's non-GLOBAL imported
        # target is not visible in this directory's scope.
        find_package(glm CONFIG REQUIRED)
        target_sources(app_profile_services_test PRIVATE
            "${profile_root}/pj_scene3D/widgets/src/urdf_package_resolver.cpp")
        target_include_directories(app_profile_services_test PRIVATE
            "${profile_root}/pj_scene3D/widgets/src"
            "${profile_root}/pj_scene3D/core/include")
        target_link_libraries(app_profile_services_test PRIVATE glm::glm)
        target_compile_definitions(app_profile_services_test PRIVATE PJ_PROFILE_WITH_URDF)
    endif()
    if(MSVC)
        target_compile_options(app_profile_services_test PRIVATE /W4 /WX /permissive- /utf-8)
    else()
        target_compile_options(app_profile_services_test PRIVATE -Wall -Wextra -Wshadow -Wconversion -Wpedantic -Werror)
    endif()
    add_test(NAME AppProfile.RuntimeServices
        COMMAND app_profile_services_test "${CMAKE_CURRENT_BINARY_DIR}/test-data")
    set_tests_properties(AppProfile.RuntimeServices PROPERTIES TIMEOUT 60)
endif()
