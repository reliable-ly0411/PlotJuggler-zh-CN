# SPDX-License-Identifier: MPL-2.0
include_guard(GLOBAL)

# Qt's text logger is the evidence source, even when Windows does not forward
# its console output. Keep the child deadline inside CTest's outer deadline so
# the wrapper can reap the process and preserve its partial failure log.
function(pj_add_logged_qt_test name target)
    cmake_parse_arguments(QT_LOG "" "TIMEOUT" "ARGS" ${ARGN})
    if(QT_LOG_UNPARSED_ARGUMENTS OR NOT QT_LOG_TIMEOUT MATCHES "^[0-9]+$" OR QT_LOG_TIMEOUT LESS_EQUAL 5)
        message(FATAL_ERROR "pj_add_logged_qt_test requires TIMEOUT > 5 seconds")
    endif()
    find_package(Python3 REQUIRED MODULE COMPONENTS Interpreter)
    math(EXPR child_timeout "${QT_LOG_TIMEOUT} - 5")
    add_test(NAME "${name}" COMMAND "${Python3_EXECUTABLE}"
        "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/run_qt_test.py"
        --timeout "${child_timeout}" -- "$<TARGET_FILE:${target}>" ${QT_LOG_ARGS})
    set_tests_properties("${name}" PROPERTIES TIMEOUT "${QT_LOG_TIMEOUT}")
endfunction()
