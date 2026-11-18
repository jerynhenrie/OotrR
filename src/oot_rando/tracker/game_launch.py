"""Start native Linux Hookshot as a child of this application.

With Yama's ptrace_scope at 1 (most distributions), ``/proc/<pid>/mem`` of the game opens only for
a process that started it: the tracker and the Archipelago client read and write the game they
launched (docs/LINUX.md). The command is what Hookshot's own launcher runs (``hookshot-launch``):
``cd <game> && exec ./bin/hookshot``, without the variables of a bundled runtime.

A separate instance (randomizer seeds beside an untouched game) passes its own mods folder (HOS_MODS)
and user folder (``--user``: saves, caches); its save backups go to ``<user>/save-backups``
(HOS_SAVE_BACKUPS), so the game never restores the other instance's saves into an empty folder.
"""
import os
import subprocess
from pathlib import Path

from oot_rando.pc_port import is_elf, is_port_folder, port_exe

BUNDLE_PREFIXES = ('HOOKSHOT_', 'PYTHON', 'APPDIR', 'APPIMAGE', 'ARGV0', 'OWD')


def launch_command(folder, user_dir=None):
    """The command that starts the game of port ``folder`` (with ``--user user_dir``); ValueError when it
    holds no Linux game."""
    folder = Path(folder)
    if not is_port_folder(folder):
        raise ValueError(f'{folder} is not a Hookshot game folder (image.bin and romfs)')
    exe = port_exe(folder)
    if exe is None or not is_elf(exe):
        raise ValueError(f'{folder} has no Linux game (bin/hookshot)')
    return [str(exe)] + (['--user', str(user_dir)] if user_dir else [])


def launch_env(environ, mods_dir=None, user_dir=None):
    """``environ`` without the variables of a bundled runtime (a frozen build's LD_LIBRARY_PATH...), plus
    the instance's mods folder and save backup folder when given."""
    env = {name: value for name, value in environ.items()
           if name != 'LD_LIBRARY_PATH' and not name.startswith(BUNDLE_PREFIXES)}
    if mods_dir:
        env['HOS_MODS'] = str(mods_dir)
    if user_dir:
        env['HOS_SAVE_BACKUPS'] = str(Path(user_dir) / 'save-backups')
    return env


def launch(folder, user_dir=None, mods_dir=None):
    """Start the game of port ``folder`` as a child process (``subprocess.Popen``)."""
    return subprocess.Popen(launch_command(folder, user_dir), cwd=str(folder),
                            env=launch_env(os.environ, mods_dir, user_dir),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
