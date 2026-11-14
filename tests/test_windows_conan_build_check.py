import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / 'scripts/windows_conan_build_check.py'
spec = importlib.util.spec_from_file_location('build_check', script)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class GraphChecks(unittest.TestCase):
    def graph(self):
        return {'graph': {'nodes': {str(i): {'ref': r, 'context': 'host', 'package_type': 'static-library', 'binary': 'Build', 'package_id': 'id'} for i, r in enumerate(m.references())}}}

    def test_reviewed_set_and_build_arguments(self):
        self.assertEqual(len(m.build_arguments()), 23)
        self.assertIn('--build=protobuf/3.21.12', m.build_arguments())
        self.assertNotIn('--build=*', m.build_arguments())
        m.verify(self.graph())

    def test_download_cache_missing_and_graph_drift_rejected(self):
        for state in ('Download', 'Cache', 'Missing', None):
            graph = self.graph()
            graph['graph']['nodes']['0']['binary'] = state
            with self.subTest(state=state), self.assertRaises(ValueError): m.verify(graph)
        graph = self.graph()
        graph['graph']['nodes']['0']['ref'] += 'bad'
        with self.assertRaises(ValueError): m.verify(graph)
        graph = self.graph()
        graph['graph']['nodes']['99'] = {'ref': 'new/1#abc', 'context':'host', 'package_type':'shared-library', 'binary':'Build', 'package_id':'id'}
        with self.assertRaises(ValueError): m.verify(graph)

    def test_build_context_ignored(self):
        graph = self.graph()
        graph['graph']['nodes']['99'] = {'ref': 'cmake/3#abc', 'context':'build', 'package_type':'application', 'binary':'Cache', 'package_id':'id'}
        m.verify(graph)

    def test_missing_recipe_pin_rejected(self):
        lock = json.loads(m.LOCK.read_text())
        lock['requires'].remove(m.references()[0])
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'incomplete.lock'
            path.write_text(json.dumps(lock))
            with patch.object(m, 'LOCK', path), self.assertRaises(ValueError):
                m.references()

if __name__ == '__main__': unittest.main()
