# SPDX-License-Identifier: LGPL-3.0-or-later
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(GEN_LOGMSG_HDR_OUT ${CMAKE_CURRENT_BINARY_DIR}/LogMessageDescriptions.h)
file(GLOB LOG_DESCRIPTION_FILES CONFIGURE_DEPENDS LogMessageDescriptions/*.xml)
add_custom_command(
  OUTPUT ${GEN_LOGMSG_HDR_OUT}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_LogMessageDescriptions_header.py
          ${CMAKE_CURRENT_SOURCE_DIR}/LogMessageDescriptions ${GEN_LOGMSG_HDR_OUT}
  DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_LogMessageDescriptions_header.py ${LOG_DESCRIPTION_FILES}
  VERBATIM)
add_library(DataAPBin SHARED dataload_apbin.cpp dataload_apbin.h ${GEN_LOGMSG_HDR_OUT})
target_include_directories(DataAPBin PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
target_link_libraries(DataAPBin PRIVATE plotjuggler_base Qt5::Core Qt5::Concurrent Qt5::Widgets Qt5::Xml Qt5::Svg)
target_compile_definitions(DataAPBin PRIVATE QT_PLUGIN LABEL_WITH_UNIT)
install(TARGETS DataAPBin DESTINATION ${PJ_PLUGIN_INSTALL_DIRECTORY})
install(FILES LICENSE COPYING.GPL3 UPSTREAM.md DESTINATION share/plotjuggler/licenses/ardupilot-apbin)
if(PJ_BUILD_FORK_TESTS)
  add_executable(apbin_test tests/apbin_test.cpp)
  set_target_properties(apbin_test PROPERTIES WIN32_EXECUTABLE FALSE RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/tests_bin")
  target_link_libraries(apbin_test PRIVATE plotjuggler_base Qt5::Core Qt5::Widgets Qt5::Xml)
  add_dependencies(apbin_test DataAPBin)
  add_test(NAME ArduPilotDataFlash COMMAND apbin_test $<TARGET_FILE:DataAPBin> ${CMAKE_CURRENT_SOURCE_DIR}/tests/synthetic.BIN)
  set_tests_properties(ArduPilotDataFlash PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
endif()
