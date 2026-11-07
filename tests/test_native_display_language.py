#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Include the pinned native-plugin display checks in source-check discovery."""
import importlib.util
from pathlib import Path
import unittest


def load_tests(loader, _tests, _pattern):
    path = Path(__file__).resolve().parents[1] / 'packaging/localization/plugin-patches/test_display_language.py'
    spec = importlib.util.spec_from_file_location('pinned_display_language_checks', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)


if __name__ == '__main__':
    unittest.main()
