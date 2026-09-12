"""Tests for copying backend/common-python/common_lambdas into the common lambda layer entry."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from common_constructs.common_lambdas_sync import sync_common_lambdas_into_layer_entry


class TestSyncCommonLambdasIntoLayerEntry(TestCase):
    def test_copies_package_into_entry(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / 'common_lambdas'
            source.mkdir()
            (source / '__init__.py').write_text('VALUE = 1\n', encoding='utf-8')
            entry = tmp_path / 'common'
            entry.mkdir()

            dest = sync_common_lambdas_into_layer_entry(entry, source=source)

            self.assertEqual(dest, entry / 'common_lambdas')
            self.assertTrue((dest / '__init__.py').is_file())
            self.assertEqual((dest / '__init__.py').read_text(encoding='utf-8'), 'VALUE = 1\n')

    def test_replaces_existing_copy(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / 'common_lambdas'
            source.mkdir()
            (source / '__init__.py').write_text('VALUE = 2\n', encoding='utf-8')
            entry = tmp_path / 'common'
            dest = entry / 'common_lambdas'
            dest.mkdir(parents=True)
            (dest / 'stale.py').write_text('stale\n', encoding='utf-8')

            sync_common_lambdas_into_layer_entry(entry, source=source)

            self.assertFalse((dest / 'stale.py').exists())
            self.assertEqual((dest / '__init__.py').read_text(encoding='utf-8'), 'VALUE = 2\n')

    def test_skips_missing_entry_directory(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            result = sync_common_lambdas_into_layer_entry(tmp_path / 'missing', source=tmp_path / 'common_lambdas')
            self.assertIsNone(result)

    def test_skips_fixture_directories(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fixtures_entry = tmp_path / 'fixtures' / 'lambdas' / 'python' / 'common'
            fixtures_entry.mkdir(parents=True)
            source = tmp_path / 'common_lambdas'
            source.mkdir()
            (source / '__init__.py').write_text('', encoding='utf-8')

            result = sync_common_lambdas_into_layer_entry(fixtures_entry, source=source)

            self.assertIsNone(result)
            self.assertFalse((fixtures_entry / 'common_lambdas').exists())

    def test_raises_when_source_is_missing(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            entry = tmp_path / 'common'
            entry.mkdir()

            with self.assertRaises(FileNotFoundError):
                sync_common_lambdas_into_layer_entry(entry, source=tmp_path / 'missing-common_lambdas')
