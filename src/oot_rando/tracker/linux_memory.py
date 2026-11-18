"""Live memory of native Linux Hookshot (or Longshot) through ``/proc/<pid>/mem``.

Same surface as ``live_memory.ProcessMemory`` (attach, read, write, close; pid, image, base, slot),
so ``LiveGameData`` and ``set_bool_in`` work unchanged: Hookshot maps guest memory at the same fixed
host address on Linux as on Windows (``A64_HOST_BASE``).

Most distributions set Yama's ptrace_scope to 1: ``/proc/<pid>/mem`` of a process opens only for its
parent (or ancestor), or with CAP_SYS_PTRACE. The client therefore starts the game itself
(``game_launch``); a game started elsewhere is reported with the way out (docs/LINUX.md).
Linux emulators are not supported.
"""
import os
import time
from pathlib import Path

from oot_rando.pc_port import is_port_process
from oot_rando.tracker.live_memory import GAMEDATA_SLOT, HOST_BASE, LiveUnavailable

PERMISSION_HINT = ('cannot read the game (Linux ptrace_scope): start it with ap-client --launch '
                   '(or Launch game), see docs/LINUX.md')


def port_pids(proc_root):
    """(pid, exe path) of every running port game under ``proc_root`` (``/proc``), in pid order."""
    found = []
    try:
        entries = list(Path(proc_root).iterdir())
    except OSError:
        return found
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            image = os.readlink(entry / 'exe')
        except OSError:
            continue
        if is_port_process(image):
            found.append((int(entry.name), image))
    return sorted(found)


class LinuxProcessMemory:
    """pread/pwrite on ``<proc_root>/<pid>/mem`` of the running game.

    ``base``: host address of guest address 0; ``slot``: guest address of the GameData slot.
    """
    def __init__(self, proc_root=Path('/proc'), host_base=HOST_BASE):
        self.proc_root = Path(proc_root)
        self.fd, self.pid, self.next_scan = None, None, 0.0
        self.image = ''
        self.base, self.slot = host_base, GAMEDATA_SLOT

    def _mem(self, pid):
        return str(self.proc_root / str(pid) / 'mem')

    def attach(self):
        if self.fd is not None:
            if (self.proc_root / str(self.pid)).exists():
                return
            self.close()
        now = time.monotonic()
        if now < self.next_scan:
            raise LiveUnavailable('game not running')
        self.next_scan = now + 5   # scanning every process each second would be wasteful
        denied = False
        for pid, image in port_pids(self.proc_root):
            try:
                fd = os.open(self._mem(pid), os.O_RDONLY)
            except PermissionError:
                denied = True
                continue
            except OSError:
                continue
            if self._probe(fd):
                self.fd, self.pid, self.image = fd, pid, image
                return
            os.close(fd)
        if denied:
            raise LiveUnavailable(PERMISSION_HINT)
        raise LiveUnavailable('game not running')

    def _probe(self, fd):
        """The game's guest window is mapped (a process still starting has none yet)."""
        try:
            return len(os.pread(fd, 8, self.base + self.slot)) == 8
        except OSError:
            return False

    def read(self, guest, size):
        try:
            data = os.pread(self.fd, size, self.base + guest)
        except (OSError, TypeError):
            data = b''
        if len(data) != size:
            raise LiveUnavailable(f'cannot read at {guest:#x}')
        return data

    def write(self, guest, data):
        """pwrite through a descriptor opened for this write only."""
        try:
            fd = os.open(self._mem(self.pid), os.O_RDWR)
        except OSError:
            raise LiveUnavailable('cannot open the game for writing')
        try:
            if os.pwrite(fd, data, self.base + guest) != len(data):
                raise LiveUnavailable(f'cannot write at {guest:#x}')
        except OSError:
            raise LiveUnavailable(f'cannot write at {guest:#x}')
        finally:
            os.close(fd)

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
        self.fd, self.pid, self.image = None, None, ''
