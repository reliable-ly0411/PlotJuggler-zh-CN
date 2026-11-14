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

# Boundary probes use the actual launcher, never the user's default settings.
add_test(NAME LauncherGuiAcceptanceBoundary COMMAND "${Python3_EXECUTABLE}"
  "${_pj_root}/tests/test_launcher_gui_acceptance.py" $<TARGET_FILE:plotjuggler-launcher>)
set_tests_properties(LauncherGuiAcceptanceBoundary PROPERTIES
  ENVIRONMENT "QT_QPA_PLATFORM=offscreen" TIMEOUT 90)
# The small standalone language project has only a synthetic probe sibling.
# Real product coupling is registered only when the product target exists.
if(TARGET plotjuggler)
  file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/launcher-acceptance-tests")
  add_test(NAME LauncherGuiAcceptance COMMAND "${Python3_EXECUTABLE}"
    "${_pj_root}/scripts/launcher_acceptance.py"
    --launcher $<TARGET_FILE:plotjuggler-launcher>
    --out-base "${CMAKE_BINARY_DIR}/launcher-acceptance-tests"
    --expected-version "${PJ_FORK_SEMVER}" --expected-platform offscreen)
  set_tests_properties(LauncherGuiAcceptance PROPERTIES
    ENVIRONMENT "QT_QPA_PLATFORM=offscreen" TIMEOUT 240)
  set_property(TEST LauncherGuiAcceptance APPEND PROPERTY ENVIRONMENT
    "PYTHONIOENCODING=cp1252")
endif()
