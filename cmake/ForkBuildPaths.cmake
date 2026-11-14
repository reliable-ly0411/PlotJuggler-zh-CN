# SPDX-License-Identifier: MPL-2.0
# Remap compiler-generated source paths without modifying linked artifacts.
# List additional absolute dependency roots with -DPJ_EXTRA_PREFIX_MAP_ROOTS=...
# (CMake list syntax). MSVC path mapping is handled by the Windows build driver.
set(PJ_EXTRA_PREFIX_MAP_ROOTS "" CACHE STRING
    "Additional absolute dependency roots to remap in compiler output")

if(NOT MSVC)
  include(CheckCCompilerFlag)
  include(CheckCXXCompilerFlag)
  foreach(_pj_lang IN ITEMS C CXX)
    if(CMAKE_${_pj_lang}_COMPILER_ID MATCHES "^(GNU|Clang|AppleClang)$")
      foreach(_pj_kind IN ITEMS file debug)
        set(_pj_flag "-f${_pj_kind}-prefix-map")
        if(_pj_lang STREQUAL "C")
          check_c_compiler_flag("${_pj_flag}=/pj-probe=." PJ_C_${_pj_kind}_PREFIX_MAP)
        else()
          check_cxx_compiler_flag("${_pj_flag}=/pj-probe=." PJ_CXX_${_pj_kind}_PREFIX_MAP)
        endif()
        if(NOT PJ_${_pj_lang}_${_pj_kind}_PREFIX_MAP)
          message(FATAL_ERROR "${_pj_lang} compiler does not support ${_pj_flag}")
        endif()
        foreach(_pj_root IN ITEMS "${CMAKE_SOURCE_DIR}" "${CMAKE_BINARY_DIR}")
          list(APPEND _pj_roots "${_pj_root}")
        endforeach()
        list(APPEND _pj_roots ${PJ_EXTRA_PREFIX_MAP_ROOTS})
        foreach(_pj_root IN LISTS _pj_roots)
          if(NOT IS_ABSOLUTE "${_pj_root}" OR _pj_root MATCHES "[=\n\r]")
            message(FATAL_ERROR "Prefix-map roots must be absolute paths without '=' or newlines")
          endif()
          # Generator expression confines the option to the language tested above.
          add_compile_options("$<$<COMPILE_LANGUAGE:${_pj_lang}>:${_pj_flag}=${_pj_root}=.>")
        endforeach()
        unset(_pj_roots)
      endforeach()
    endif()
  endforeach()
endif()
