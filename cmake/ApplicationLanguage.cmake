# SPDX-License-Identifier: MPL-2.0
find_package(Qt5 REQUIRED COMPONENTS Core Widgets LinguistTools)
get_filename_component(_pj_root "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
qt5_add_translation(PJ_QM_FILES
  "${_pj_root}/plotjuggler_app/translations/plotjuggler_zh_CN.ts"
  "${_pj_root}/plotjuggler_app/translations/plotjuggler_zh_TW.ts")
set(PJ_CN_QM "${CMAKE_CURRENT_BINARY_DIR}/plotjuggler_zh_CN.qm")
set(PJ_TW_QM "${CMAKE_CURRENT_BINARY_DIR}/plotjuggler_zh_TW.qm")
get_target_property(_pj_qmake Qt5::qmake IMPORTED_LOCATION)
execute_process(COMMAND "${_pj_qmake}" -query QT_INSTALL_TRANSLATIONS
  OUTPUT_VARIABLE _pj_qt_translations OUTPUT_STRIP_TRAILING_WHITESPACE)
set(PJ_QT_TRANSLATIONS_DIR "${_pj_qt_translations}" CACHE PATH "Matching Qt5 translation directory")
foreach(locale zh_CN zh_TW)
  if(NOT EXISTS "${PJ_QT_TRANSLATIONS_DIR}/qtbase_${locale}.qm")
    message(FATAL_ERROR "Required Qt5 standard dialog catalog missing: qtbase_${locale}.qm")
  endif()
endforeach()
set(PJ_QTBASE_CN_QM "${PJ_QT_TRANSLATIONS_DIR}/qtbase_zh_CN.qm")
set(PJ_QTBASE_TW_QM "${PJ_QT_TRANSLATIONS_DIR}/qtbase_zh_TW.qm")
file(SHA256 "${PJ_QTBASE_CN_QM}" PJ_QTBASE_CN_SHA256)
file(SHA256 "${PJ_QTBASE_TW_QM}" PJ_QTBASE_TW_SHA256)
configure_file("${_pj_root}/cmake/Qt5Translations.json.in"
  "${CMAKE_CURRENT_BINARY_DIR}/QT5-TRANSLATIONS.json" @ONLY)
configure_file("${_pj_root}/plotjuggler_app/translations/i18n.qrc.in"
  "${CMAKE_CURRENT_BINARY_DIR}/i18n.qrc" @ONLY)
qt5_add_resources(PJ_I18N_RESOURCES "${CMAKE_CURRENT_BINARY_DIR}/i18n.qrc")
add_custom_target(pj_translations DEPENDS ${PJ_QM_FILES})
add_library(pj_application_language STATIC
  "${_pj_root}/plotjuggler_app/app_language.cpp"
  "${_pj_root}/plotjuggler_app/app_settings.cpp" ${PJ_I18N_RESOURCES})
add_dependencies(pj_application_language pj_translations)
target_include_directories(pj_application_language PUBLIC "${_pj_root}/plotjuggler_app")
target_link_libraries(pj_application_language PUBLIC Qt5::Widgets)
