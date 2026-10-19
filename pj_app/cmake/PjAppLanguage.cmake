# SPDX-License-Identifier: MPL-2.0
include_guard(GLOBAL)
# Use the build-host interpreter, not Conan's target CPython config package.
# The latter may enforce its embedding-library version even for Interpreter.
find_package(Python3 QUIET MODULE COMPONENTS Interpreter)

# The app and the focused Qt-only tests share the same translation resources
# and implementation, without pulling the shell's SDK/rendering dependencies.
function(pj_add_app_language)
    if(TARGET pj_app_language)
        return()
    endif()
    find_package(Qt6 REQUIRED COMPONENTS Core LinguistTools)
    get_filename_component(app_dir "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/.." ABSOLUTE)
    set(ts_file "${app_dir}/translations/plotjuggler4_zh_CN.ts")
    set(qm_dir "${CMAKE_CURRENT_BINARY_DIR}/translations")

    add_library(pj_app_language STATIC
        "${app_dir}/src/AppLanguage.cpp"
        "${app_dir}/src/AppLanguage.h")
    target_include_directories(pj_app_language PUBLIC "${app_dir}/src")
    target_link_libraries(pj_app_language PUBLIC Qt6::Core)
    if(DEFINED PJ_WARNING_FLAGS)
        target_compile_options(pj_app_language PRIVATE ${PJ_WARNING_FLAGS})
    endif()

    # Qt6.9+ can merge Qt's own strings into the embedded catalog. There is no
    # runtime dependency on a developer machine's Qt translations directory.
    qt_add_lrelease(
        TS_FILES "${ts_file}"
        LRELEASE_TARGET pj_app_lrelease
        QM_OUTPUT_DIRECTORY "${qm_dir}"
        QM_FILES_OUTPUT_VARIABLE qm_files
        MERGE_QT_TRANSLATIONS
        QT_TRANSLATION_CATALOGS qtbase
        OPTIONS -nounfinished)
    qt_add_resources(pj_app_language pj_app_translations
        PREFIX "/i18n"
        BASE "${qm_dir}"
        FILES ${qm_files})
    add_dependencies(pj_app_language pj_app_lrelease)

    # Refresh only on explicit request, using the same extraction scope as the
    # coverage check. Ordinary builds must never rewrite the tracked catalog.
    if(Python3_Interpreter_FOUND)
        add_custom_target(pj_app_lupdate
            COMMAND "${Python3_EXECUTABLE}" "${app_dir}/../tests/check_translations_4x.py"
                --lupdate $<TARGET_FILE:Qt6::lupdate> --update-ts
            WORKING_DIRECTORY "${app_dir}/.."
            VERBATIM)
    endif()
endfunction()

# Both the full application build and the standalone i18n project run this
# exact executable against the production catalog (no test-only translations).
function(pj_add_app_language_test)
    find_package(Qt6 REQUIRED COMPONENTS Test)
    get_filename_component(app_dir "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/.." ABSOLUTE)
    add_executable(app_language_test "${app_dir}/tests/app_language_test.cpp")
    set_target_properties(app_language_test PROPERTIES AUTOMOC ON)
    target_link_libraries(app_language_test PRIVATE pj_app_language Qt6::Test)
    # Catalog assertions contain Chinese literals; do not use the host codepage.
    if(MSVC)
        target_compile_options(app_language_test PRIVATE /utf-8)
    endif()
    if(DEFINED PJ_WARNING_FLAGS)
        target_compile_options(app_language_test PRIVATE ${PJ_WARNING_FLAGS})
    endif()
    add_test(NAME AppLanguageTest COMMAND app_language_test)
    if(Python3_Interpreter_FOUND)
        add_test(NAME TranslationCatalog4x
            COMMAND "${Python3_EXECUTABLE}" "${app_dir}/../tests/check_translations_4x.py"
                --lupdate $<TARGET_FILE:Qt6::lupdate>)
        set_tests_properties(TranslationCatalog4x PROPERTIES WORKING_DIRECTORY "${app_dir}/..")
    endif()
endfunction()
