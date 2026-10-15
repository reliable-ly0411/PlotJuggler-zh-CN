find_package(Arrow QUIET CONFIG)

# when using conan, Parquet::parquet_static is found, otherwise
# we need to do find_package(Parquet)
if(NOT TARGET Parquet::parquet_static AND NOT TARGET Parquet::parquet_shared)
  find_package(Parquet QUIET)
endif()

if(UNIX AND NOT APPLE AND TARGET Arrow::arrow_shared AND TARGET Parquet::parquet_shared)
  # Use one shared Arrow runtime across Parquet and Mosaico on Linux. Mixing
  # static Arrow with Flight's shared Arrow dependency registers OTLP twice.
  set(PJ_PARQUET_ARROW_TARGET Arrow::arrow_shared)
  set(PJ_PARQUET_TARGET Parquet::parquet_shared)
elseif(TARGET Arrow::arrow_static AND TARGET Parquet::parquet_static)
  set(PJ_PARQUET_ARROW_TARGET Arrow::arrow_static)
  set(PJ_PARQUET_TARGET Parquet::parquet_static)
endif()

if(PJ_PARQUET_TARGET)

  message(STATUS "[Arrow/Parquet] found")

  qt5_wrap_ui(UI_SRC dataload_parquet.ui)

  set(SRC dataload_parquet.cpp)

  add_library(DataLoadParquet SHARED ${SRC} ${UI_SRC})

  target_link_libraries(
    DataLoadParquet PRIVATE Qt5::Widgets Qt5::Xml ${PJ_PARQUET_ARROW_TARGET}
                            ${PJ_PARQUET_TARGET} plotjuggler_base)

  target_compile_definitions(DataLoadParquet PRIVATE QT_PLUGIN)

  install(TARGETS DataLoadParquet DESTINATION ${PJ_PLUGIN_INSTALL_DIRECTORY})

  if(PJ_BUILD_FORK_TESTS)
    add_executable(parquet_smoke_test ${CMAKE_SOURCE_DIR}/tests/parquet_smoke_test.cpp)
    set_target_properties(parquet_smoke_test PROPERTIES WIN32_EXECUTABLE FALSE RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/tests_bin")
    target_link_libraries(parquet_smoke_test PRIVATE plotjuggler_base Qt5::Core Qt5::Widgets Qt5::Xml
                          ${PJ_PARQUET_ARROW_TARGET} ${PJ_PARQUET_TARGET})
    add_dependencies(parquet_smoke_test DataLoadParquet)
    add_test(NAME ParquetCompatibility COMMAND parquet_smoke_test $<TARGET_FILE:DataLoadParquet>)
    set_tests_properties(ParquetCompatibility PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
  endif()

else()
  message("[Parquet] not found. Skipping plugin DataLoadParquet.")
endif()
