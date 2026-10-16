# SPDX-License-Identifier: MPL-2.0
"""Export an additive official-3.17.2 Qt5/CoreGui proposal, without fork features."""
import argparse
import difflib
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
files = {
    'plotjuggler_app/resource_image.h': (root/'plotjuggler_app/resource_image.h').read_text(encoding='utf-8'),
    'plotjuggler_app/resource_image.cpp': (root/'plotjuggler_app/resource_image.cpp').read_text(encoding='utf-8'),
    'tests/resource_image_variant_test.cpp': (root/'tests/resource_image_test.cpp').read_text(encoding='utf-8'),
    'tests/resource_image_variant/CMakeLists.txt': '''# SPDX-License-Identifier: MPL-2.0
cmake_minimum_required(VERSION 3.16)
project(GenericResourceImageVariant LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(Qt5 REQUIRED COMPONENTS Core Gui)
message(STATUS "Official 3.17.2 helper: Qt ${Qt5Core_VERSION}; C++${CMAKE_CXX_STANDARD}")
enable_testing()
add_executable(resource_image_variant_test
  ../../plotjuggler_app/resource_image.cpp ../resource_image_variant_test.cpp)
target_include_directories(resource_image_variant_test PRIVATE ../../plotjuggler_app)
target_link_libraries(resource_image_variant_test PRIVATE Qt5::Core Qt5::Gui)
add_test(NAME GenericResourceImage COMMAND resource_image_variant_test)
set_tests_properties(GenericResourceImage PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
set(PJ_UPSTREAM_ENGLISH_DIR "" CACHE PATH "Official 3.17.2 English image directory")
if(PJ_UPSTREAM_ENGLISH_DIR)
  add_test(NAME DefaultEnglishImages COMMAND resource_image_variant_test "${PJ_UPSTREAM_ENGLISH_DIR}")
  set_tests_properties(DefaultEnglishImages PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
endif()
'''}
patch = []
for path, text in files.items():
    lines = text.replace('\r\n','\n').splitlines(keepends=True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    patch += [f'diff --git a/{path} b/{path}\n', 'new file mode 100644\n']
    patch += list(difflib.unified_diff([], lines, fromfile='/dev/null', tofile='b/'+path))
destination = Path(a.out)
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(''.join(patch), encoding='utf-8', newline='\n')
print('Exported four additive MPL-2.0 Core/Gui files; application default behavior unchanged.')
