import _src_path  # noqa: F401  (src on sys.path)
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from oot_rando.tracker.game_launch import launch_command, launch_env


class GameLaunchTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.tmp = Path(self.directory.name)
        self.port = self.tmp / 'Switch2'
        (self.port / 'bin').mkdir(parents=True)
        (self.port / 'romfs').mkdir()
        (self.port / 'image.bin').touch()
        (self.port / 'bin' / 'hookshot').write_bytes(b'\x7fELF\x02\x01\x01')
        (self.port / 'hookshot').write_bytes(b'#!/bin/sh\n')

    def tearDown(self):
        self.directory.cleanup()

    def test_launch_command_uses_game_binary(self):
        with mock.patch('os.name', 'posix'):
            self.assertEqual(launch_command(self.port), [str(self.port / 'bin' / 'hookshot')])

    def test_launch_rejects_non_port_folder(self):
        (self.tmp / 'not-a-port').mkdir()
        with self.assertRaises(ValueError):
            launch_command(self.tmp / 'not-a-port')

    def test_launch_rejects_port_without_linux_binary(self):
        (self.port / 'bin' / 'hookshot').unlink()
        with mock.patch('os.name', 'posix'), self.assertRaises(ValueError):
            launch_command(self.port)

    def test_launch_command_passes_user_folder(self):
        with mock.patch('os.name', 'posix'):
            self.assertEqual(launch_command(self.port, user_dir=self.tmp / 'rando'),
                             [str(self.port / 'bin' / 'hookshot'), '--user', str(self.tmp / 'rando')])

    def test_launch_env_points_mods_and_backups_at_the_instance(self):
        env = launch_env({'HOME': '/home/me'}, mods_dir='/g/mods-rando', user_dir='/d/hookshot-rando')
        self.assertEqual(env, {'HOME': '/home/me', 'HOS_MODS': '/g/mods-rando',
                               'HOS_SAVE_BACKUPS': str(Path('/d/hookshot-rando') / 'save-backups')})

    def test_launch_env_drops_bundle_variables(self):
        env = launch_env({'HOME': '/home/me', 'LD_LIBRARY_PATH': '/tmp/_MEI1', 'PYTHONHOME': '/x',
                          'APPIMAGE': '/a', 'APPDIR': '/b', 'HOOKSHOT_BUILDER_EXE': '/c', 'DISPLAY': ':0'})
        self.assertEqual(env, {'HOME': '/home/me', 'DISPLAY': ':0'})


class GuiLaunchGameTest(unittest.TestCase):
    def test_second_click_while_game_runs_does_not_start_another(self):
        from oot_rando.gui import randomizer_gui
        app = mock.Mock(spec=['hookshot_root', 'game_process'])
        app.hookshot_root.return_value = Path('/games/Switch2')
        app.game_process = mock.Mock(**{'poll.return_value': None})   # still running
        with mock.patch('oot_rando.tracker.game_launch.launch') as launch, \
                mock.patch.object(randomizer_gui.messagebox, 'showinfo'):
            randomizer_gui.Application.launch_game(app)
        launch.assert_not_called()


class GuiLaunchButtonTest(unittest.TestCase):
    def test_gui_has_what_the_launch_button_needs(self):
        from oot_rando.gui import randomizer_gui
        self.assertTrue(hasattr(randomizer_gui, 'sys'))   # the button is shown when sys.platform is linux
        self.assertTrue(callable(getattr(randomizer_gui.Application, 'launch_game', None)))


if __name__ == '__main__':
    unittest.main()
