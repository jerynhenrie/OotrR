# Linux: live reading and Archipelago items with Hookshot

The tracker and the Archipelago client read the running game's memory to see checks
before the game saves, and write one flag to hand over items from other worlds. On
Linux this goes through `/proc/<pid>/mem` of native Hookshot (or Longshot).
Linux emulators are not supported.

## Where things are

- The game process is `<game>/bin/hookshot`. `<game>/hookshot` is a shell launcher
  that opens Hookshot Builder; it is not the game.
- Guest memory sits at the same fixed host address as on Windows (`0x100000000000`),
  so the reading code is shared.
- Saves are in `$XDG_DATA_HOME/hookshot/save` (`~/.local/share/hookshot/save` by
  default), not in `<game>/user/save`. The tracker looks in both.

## Permission: start the game from the client

Most distributions set the Yama `ptrace_scope` to `1`
(`cat /proc/sys/kernel/yama/ptrace_scope`). A program may then read the memory of
the processes it started, and of no other. A game started from the desktop
menu, the builder or a terminal cannot be read by the client: opening
`/proc/<pid>/mem` fails with `Permission denied`.

Start the game from the client instead:

- headless: `python -m oot_rando ap-client MOD_FOLDER SERVER --launch`
- application: **Launch game** in the Archipelago row of the Tracker tab.

The client starts `bin/hookshot` in the game folder, as Hookshot's own launcher
does (`cd <game> && exec ./bin/hookshot`), and reads it as its child.

If you would rather start the game yourself, give the permission to a
dedicated copy of the Python interpreter that runs the client (never to the
system Python, which every script on the PC uses):

```sh
cp "$(readlink -f "$(command -v python3)")" ~/.local/share/oot-rando-python
sudo setcap cap_sys_ptrace=ep ~/.local/share/oot-rando-python
```

`CAP_SYS_PTRACE` lets that interpreter read and change any of your processes.
Setting `ptrace_scope` to `0` does the same for every program, and is not
recommended.

## Tested

Hookshot v2.3.2, Arch Linux (Omarchy), kernel 7.2, `ptrace_scope` 1, 2026-11-17:

- Started by the client: the snapshot read 11292 GameData bools and the
  Bool64bitKey table 8 seconds after launch, at the title screen.
- Started from the builder or as a user service: `LiveUnavailable: cannot read
  the game (Linux ptrace_scope): start it with ap-client --launch (or Launch game),
  see docs/LINUX.md`. With both running, the client skips the one it cannot read
  and attaches to the one it started.
- Multiworld (Archipelago 0.6.7, local server, OoT Remake + ChecksFinder):
  the Kokiri Sword chest reached the server 4 seconds before the game wrote its
  save (live reading); after `/release` of the other world, Link held up each of
  its 11 items in turn (reception through `/proc/<pid>/mem`).
- Server `/send` items are never handed over (they have no mailbox record), on
  any system: test reception with items found in another world.
