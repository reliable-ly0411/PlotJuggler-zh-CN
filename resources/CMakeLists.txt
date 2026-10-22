# SPDX-License-Identifier: MPL-2.0
if(EMSCRIPTEN)
    add_library(pj_resources OBJECT resources.qrc)
    set_target_properties(pj_resources PROPERTIES AUTORCC ON)
    target_link_libraries(pj_resources PRIVATE Qt6::Core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(pj_resources PRIVATE -g0)
    endif()
else()
    # Qt's two-pass resource compiler embeds the reviewed image pool directly
    # in one native object, without compiling a large C++ byte array.
    # Keep lossless savings below rcc's default 70% threshold too; the input
    # assets and the bytes returned by Qt's resource API stay unchanged.
    qt6_add_big_resources(pj_resource_objects resources.qrc OPTIONS --threshold 0)
    add_custom_target(pj_resources_object DEPENDS ${pj_resource_objects})
    add_library(pj_resources INTERFACE)
    add_dependencies(pj_resources pj_resources_object)
    # Link the object itself into every consumer: a static archive could drop
    # its unreferenced resource initializer. The dependency also covers callers
    # in other directories and builds of a single consumer target.
    target_link_libraries(pj_resources INTERFACE ${pj_resource_objects} Qt6::Core)
endif()
