"""Native PC ports of the game (Hookshot, its successor Longshot, and any later fork).

They all share one layout: ``<game>/<name>.exe`` next to ``image.bin`` and ``romfs/``, with the
mods in ``<game>/mods`` and the options in ``<game>/<name>_options.ini``. Longshot's launcher
builds (one folder per version, ``Games/Longshot/<version>``) keep the exe in ``<game>/bin/``. Nothing here depends on
the exe's name: a folder holding ``image.bin`` and ``romfs`` is a port, and a running process is
the port when its exe sits in such a folder (or carries one of the known names).

Native Linux builds keep the game in ``<game>/bin/hookshot`` (an ELF file, no suffix); ``<game>/hookshot``
beside it is a shell launcher that opens the builder, not the game.
"""
import os
from pathlib import Path

KNOWN_EXES = ('hookshot.exe', 'longshot.exe')
KNOWN_POSIX_EXES = ('hookshot', 'longshot')
ELF_MAGIC = b'\x7fELF'
DEFAULT_OPTIONS = 'hookshot_options.ini'


def is_port_folder(folder):
    """True when ``folder`` holds a built port: ``image.bin`` and ``romfs/``."""
    if not folder:
        return False
    folder = Path(folder)
    try:
        return (folder / 'image.bin').is_file() and (folder / 'romfs').is_dir()
    except OSError:
        return False


EXE_FOLDERS = ('.', 'bin')   # where a port keeps its exe, relative to the game folder


def port_exe(folder):
    """The game exe of a port folder (or its ``bin/``): a known name first, else the first other ``*.exe``."""
    folder = Path(folder)
    places = [folder / sub for sub in EXE_FOLDERS]
    for place in places:
        for name in KNOWN_EXES:
            if (place / name).is_file():
                return place / name
    for place in places:
        try:
            exes = sorted(p for p in place.glob('*.exe') if p.is_file())
        except OSError:
            continue
        if exes:
            return exes[0]
    if os.name != 'nt':
        for place in places:
            for name in KNOWN_POSIX_EXES:
                if is_elf(place / name):
                    return place / name
    return None


def is_elf(path):
    """True when ``path`` is a file starting with the ELF magic (a Linux binary, not a script)."""
    try:
        with open(path, 'rb') as file:
            return file.read(4) == ELF_MAGIC
    except OSError:
        return False


def game_folder(image_path):
    """The port folder of a running exe: its own folder, or the one above ``bin/``; else None."""
    if not image_path:
        return None
    parent = Path(image_path).parent
    for folder in (parent, parent.parent if parent.name.lower() == 'bin' else None):
        if folder is not None and folder != Path('.') and is_port_folder(folder):
            return folder
    return None


def is_port_process(image_path):
    """True when a process image (full path, or bare name) is a port's game exe."""
    if not image_path:
        return False
    path = Path(image_path)
    if path.suffix == '' and path.name.lower() in KNOWN_POSIX_EXES:
        return game_folder(path) is not None and is_elf(path)
    if path.suffix.lower() != '.exe':
        return False
    if path.name.lower() in KNOWN_EXES:
        return True
    return path.parent != Path('.') and game_folder(path) is not None


def options_ini(folder):
    """The port's options ini: ``<exe stem>_options.ini``, else any ``*_options.ini``, else Hookshot's."""
    folder = Path(folder)
    exe = port_exe(folder) if folder.is_dir() else None
    own = folder / (exe.stem.lower() + '_options.ini') if exe else folder / DEFAULT_OPTIONS
    if own.exists():
        return own
    try:
        found = sorted(folder.glob('*_options.ini'))
    except OSError:
        found = []
    return found[0] if found else own
