# SPDX-License-Identifier: MPL-2.0
"""Export an additive Qt6/CoreGui proposal; no locale, catalog, plugin or fork CI."""
import argparse
import difflib
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
files = {
    'pj_app/src/resource_image.h': (root/'plotjuggler_app/resource_image.h').read_text(encoding='utf-8'),
    'pj_app/src/resource_image.cpp': (root/'plotjuggler_app/resource_image.cpp').read_text(encoding='utf-8'),
    'pj_app/tests/resource_image_variant_test.cpp': (root/'tests/resource_image_test.cpp').read_text(encoding='utf-8'),
    'pj_app/tests/resource_image_variant/CMakeLists.txt': '''# SPDX-License-Identifier: MPL-2.0
cmake_minimum_required(VERSION 3.22)
project(GenericResourceImageVariant LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(Qt6 6.11 REQUIRED COMPONENTS Core Gui)
enable_testing()
add_executable(resource_image_variant_test
  ../../src/resource_image.cpp ../resource_image_variant_test.cpp)
target_include_directories(resource_image_variant_test PRIVATE ../../src)
target_link_libraries(resource_image_variant_test PRIVATE Qt6::Core Qt6::Gui)
add_test(NAME GenericResourceImage COMMAND resource_image_variant_test)
set_tests_properties(GenericResourceImage PROPERTIES ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
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
