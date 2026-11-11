# SPDX-License-Identifier: MPL-2.0
get_filename_component(_pj_root "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_executable(pj_language_probe "${_pj_root}/tests/language_probe.cpp")
target_link_libraries(pj_language_probe PRIVATE pj_application_language)
set_target_properties(pj_language_probe PROPERTIES WIN32_EXECUTABLE FALSE
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/tests_bin")
add_test(NAME ApplicationLanguages COMMAND "${Python3_EXECUTABLE}"
  "${_pj_root}/tests/test_application_language.py" $<TARGET_FILE:pj_language_probe>
  $<TARGET_FILE:plotjuggler-launcher>)
set_tests_properties(ApplicationLanguages PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen" TIMEOUT 60)
add_test(NAME TranslationCatalogs COMMAND "${Python3_EXECUTABLE}"
  "${_pj_root}/tests/check_translations.py" --fresh)
set_tests_properties(TranslationCatalogs PROPERTIES
  ENVIRONMENT "LUPDATE=$<TARGET_FILE:Qt5::lupdate>")
add_test(NAME TranslationValidatorUnit COMMAND "${Python3_EXECUTABLE}"
  "${_pj_root}/tests/test_translation_validation.py")
