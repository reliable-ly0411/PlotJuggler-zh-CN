# SPDX-License-Identifier: MPL-2.0
# Public product version policy: additive Qt5 functionality is a minor release.
set(PJ_UPSTREAM_VERSION "3.17.2")
set(PJ_FORK_PRERELEASE "zh.2")
set(PJ_ARDUPILOT_REVISION "1")
find_package(Git QUIET)
set(PJ_FORK_GIT_REVISION "source")
if(GIT_FOUND)
  execute_process(COMMAND ${GIT_EXECUTABLE} rev-parse --short=12 HEAD
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE _pj_git_revision OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET RESULT_VARIABLE _pj_git_result)
  if(_pj_git_result EQUAL 0)
    set(PJ_FORK_GIT_REVISION "${_pj_git_revision}")
  endif()
endif()
set(PJ_FORK_SEMVER
  "${PROJECT_VERSION}-${PJ_FORK_PRERELEASE}+upstream.${PJ_UPSTREAM_VERSION}.apbin.${PJ_ARDUPILOT_REVISION}.g${PJ_FORK_GIT_REVISION}")
configure_file(${CMAKE_SOURCE_DIR}/cmake/ForkVersion.json.in
               ${CMAKE_BINARY_DIR}/FORK-VERSION.json @ONLY)
