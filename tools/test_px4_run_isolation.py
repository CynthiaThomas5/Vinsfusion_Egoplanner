#!/usr/bin/env python3
from pathlib import Path
import tempfile
import unittest

from prepare_px4_run import prepare


class RunIsolationTests(unittest.TestCase):
    def test_no_historical_state_import_or_source_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'source', root / 'run'
            for name in ('bin', 'etc', 'rootfs', 'log', 'eeprom'):
                (source / name).mkdir(parents=True)
            (source / 'bin/px4').write_bytes(b'unit-test fixture')
            (source / 'etc/config').write_text('source config')
            (source / 'rootfs/etc').symlink_to(source / 'etc')
            for parent in (source, source / 'rootfs'):
                for name in ('parameters.bson', 'parameters_backup.bson', 'dataman'):
                    (parent / name).write_bytes(b'historical state')
            (source / 'log/old.ulg').write_bytes(b'historical log')
            (source / 'eeprom/old').write_bytes(b'historical storage')
            prepare(source, output)
            for parent in (output, output / 'rootfs'):
                for name in ('parameters.bson', 'parameters_backup.bson', 'dataman'):
                    self.assertFalse((parent / name).exists())
                    (parent / name).write_bytes(b'new run state')
                    self.assertEqual((source / parent.relative_to(output) / name).read_bytes(),
                                     b'historical state')
            (output / 'rootfs/etc/config').write_text('run config')
            self.assertEqual((source / 'etc/config').read_text(), 'source config')
            self.assertEqual(list((output / 'log').iterdir()), [])
            self.assertEqual(list((output / 'eeprom').iterdir()), [])
            self.assertTrue((output / 'bin').is_symlink())
            with self.assertRaises(FileExistsError):
                prepare(source, output)
            with self.assertRaisesRegex(ValueError, 'outside'):
                prepare(source, source / 'nested-run')


if __name__ == '__main__':
    unittest.main()
