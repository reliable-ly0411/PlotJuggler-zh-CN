# SPDX-License-Identifier: MPL-2.0
# Optional fully specified offline inputs for the synthetic IFW resource test.
# An incomplete override must not silently fall back to a network download.
include_guard(GLOBAL)
set(PJ_IFW_TEST_ARCHIVE "" CACHE FILEPATH "Pinned IFW archive for the Windows test")
set(PJ_IFW_TEST_EXTRACTOR "" CACHE FILEPATH "Verified 7z executable for the Windows test")
set(PJ_IFW_TEST_EXTRACTOR_SHA256 "" CACHE STRING "Verified SHA-256 of the 7z executable")
set(PJ_IFW_TEST_ARGS)
if(NOT "${PJ_IFW_TEST_ARCHIVE}" STREQUAL "" OR NOT "${PJ_IFW_TEST_EXTRACTOR}" STREQUAL ""
   OR NOT "${PJ_IFW_TEST_EXTRACTOR_SHA256}" STREQUAL "")
    if("${PJ_IFW_TEST_ARCHIVE}" STREQUAL "" OR "${PJ_IFW_TEST_EXTRACTOR}" STREQUAL ""
       OR "${PJ_IFW_TEST_EXTRACTOR_SHA256}" STREQUAL "")
        message(FATAL_ERROR "Offline IFW tests require archive, extractor and extractor SHA-256 together")
    endif()
    foreach(path IN ITEMS PJ_IFW_TEST_ARCHIVE PJ_IFW_TEST_EXTRACTOR)
        if(NOT IS_ABSOLUTE "${${path}}" OR NOT EXISTS "${${path}}" OR IS_DIRECTORY "${${path}}")
            message(FATAL_ERROR "${path} must name an existing absolute file")
        endif()
    endforeach()
    string(TOLOWER "${PJ_IFW_TEST_EXTRACTOR_SHA256}" _pj_ifw_extractor_sha)
    string(LENGTH "${_pj_ifw_extractor_sha}" _pj_ifw_extractor_sha_length)
    if(NOT _pj_ifw_extractor_sha_length EQUAL 64 OR NOT _pj_ifw_extractor_sha MATCHES "^[0-9a-f]+$")
        message(FATAL_ERROR "PJ_IFW_TEST_EXTRACTOR_SHA256 must be a SHA-256 hex digest")
    endif()
    list(APPEND PJ_IFW_TEST_ARGS --ifw-archive "${PJ_IFW_TEST_ARCHIVE}"
        --extractor "${PJ_IFW_TEST_EXTRACTOR}" --extractor-sha256 "${_pj_ifw_extractor_sha}")
endif()
