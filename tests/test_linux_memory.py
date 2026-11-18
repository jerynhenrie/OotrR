import _src_path  # noqa: F401  (src on sys.path)
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from oot_rando.tracker.live_memory import (LiveGameData, LiveUnavailable, ProcessMemory, SEQUENCE_IS_CHILDHOOD,
                                           make_process_memory, set_bool_in)
from test_live_memory import gamedata_image

KEY = 0x12345678
TEST_BASE = 0x1000   # host offset of guest 0 in the fake mem file (HOST_BASE is 16 TiB: past ext4's file size limit)


@unittest.skipUnless(hasattr(os, 'pread'), 'Linux /proc backend')
class LinuxMemoryTest(unittest.TestCase):
    """A fake /proc: <root>/<pid>/exe links to a port's bin/hookshot, <root>/<pid>/mem holds guest memory."""
    def setUp(self):
        from oot_rando.tracker.linux_memory import LinuxProcessMemory, port_pids
        self.Memory, self.port_pids = LinuxProcessMemory, port_pids
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        port = base / 'Switch2'
        (port / 'bin').mkdir(parents=True)
        (port / 'romfs').mkdir()
        (port / 'image.bin').touch()
        (port / 'bin' / 'hookshot').write_bytes(b'\x7fELF\x02\x01\x01')
        other = base / 'other'
        other.mkdir()
        (other / 'bash').write_bytes(b'\x7fELF\x02\x01\x01')
        self.root = base / 'proc'
        self.make_process(4242, port / 'bin' / 'hookshot',
                          gamedata_image({SEQUENCE_IS_CHILDHOOD: True, KEY: False}))
        self.make_process(17, other / 'bash', {})
        (self.root / 'self').mkdir()   # not a pid: skipped

    def make_process(self, pid, exe, image):
        folder = self.root / str(pid)
        folder.mkdir(parents=True)
        (folder / 'exe').symlink_to(exe)
        with open(folder / 'mem', 'wb') as mem:
            for guest, data in image.items():
                mem.seek(TEST_BASE + guest)
                mem.write(data)

    def memory(self):
        return self.Memory(self.root, host_base=TEST_BASE)

    def tearDown(self):
        self.directory.cleanup()

    def test_port_pids_finds_only_port(self):
        self.assertEqual([pid for pid, _ in self.port_pids(self.root)], [4242])

    def test_snapshot_through_fake_proc(self):
        data = LiveGameData(self.memory())
        self.assertTrue(data.snapshot()['bool'][SEQUENCE_IS_CHILDHOOD])

    def test_set_bool_writes_value_byte(self):
        data = LiveGameData(self.memory())
        self.assertTrue(set_bool_in(data, KEY, True))
        self.assertTrue(LiveGameData(self.memory()).snapshot()['bool'][KEY])

    def test_attach_after_game_exit_rescans(self):
        memory = self.memory()
        memory.attach()
        self.assertEqual(memory.pid, 4242)
        shutil.rmtree(self.root / '4242')
        memory.next_scan = 0
        with self.assertRaisesRegex(LiveUnavailable, 'game not running'):
            memory.attach()
        self.assertIsNone(memory.pid)

    def test_permission_denied_explains_fix(self):
        with mock.patch('os.open', side_effect=PermissionError(13, 'Permission denied')):
            with self.assertRaisesRegex(LiveUnavailable, r'--launch.*LINUX\.md'):
                self.memory().attach()

    def test_permission_hint_kept_between_scans(self):
        # The delivery loop polls every second; scans are 5 s apart: the hint must not turn into 'game not running'.
        memory = self.memory()
        with mock.patch('os.open', side_effect=PermissionError(13, 'Permission denied')):
            for _ in range(3):
                with self.assertRaisesRegex(LiveUnavailable, r'--launch.*LINUX\.md'):
                    memory.attach()


class FactoryTest(unittest.TestCase):
    def test_factory_picks_platform_class(self):
        with mock.patch('os.name', 'nt'), mock.patch('ctypes.WinDLL', mock.MagicMock(), create=True):
            self.assertIsInstance(make_process_memory(), ProcessMemory)
        with mock.patch('os.name', 'posix'), mock.patch('sys.platform', 'linux'):
            from oot_rando.tracker.linux_memory import LinuxProcessMemory
            self.assertIsInstance(make_process_memory(), LinuxProcessMemory)
        with mock.patch('os.name', 'posix'), mock.patch('sys.platform', 'darwin'):
            with self.assertRaises(LiveUnavailable):
                make_process_memory()


if __name__ == '__main__':
    unittest.main()
