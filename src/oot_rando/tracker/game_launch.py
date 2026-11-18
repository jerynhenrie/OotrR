"""Start native Linux Hookshot as a child of this application.

With Yama's ptrace_scope at 1 (most distributions), ``/proc/<pid>/mem`` of the game opens only for
a process that started it: the tracker and the Archipelago client read and write the game they
launched (docs/LINUX.md). The command is what Hookshot's own launcher runs (``hookshot-launch``):
``cd <game> && exec ./bin/hookshot``, without the variables of a bundled runtime.
"""
import os
import subprocess
from pathlib import Path

from oot_rando.pc_port import is_elf, is_port_folder, port_exe

BUNDLE_PREFIXES = ('HOOKSHOT_', 'PYTHON', 'APPDIR', 'APPIMAGE', 'ARGV0', 'OWD')


def launch_command(folder):
    """The command that starts the game of port ``folder``; ValueError when it holds no Linux game."""
    folder = Path(folder)
    if not is_port_folder(folder):
        raise ValueError(f'{folder} is not a Hookshot game folder (image.bin and romfs)')
    exe = port_exe(folder)
    if exe is None or not is_elf(exe):
        raise ValueError(f'{folder} has no Linux game (bin/hookshot)')
    return [str(exe)]


def launch_env(environ):
    """``environ`` without the variables of a bundled runtime (a frozen build's LD_LIBRARY_PATH...)."""
    return {name: value for name, value in environ.items()
            if name != 'LD_LIBRARY_PATH' and not name.startswith(BUNDLE_PREFIXES)}


def launch(folder):
    """Start the game of port ``folder`` as a child process (``subprocess.Popen``)."""
    return subprocess.Popen(launch_command(folder), cwd=str(folder), env=launch_env(os.environ),
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
