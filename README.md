# Number Grove

An arithmetic garden game with calm and adventure play for grades 1–6.

A community plugin for **Omarchy Quattro with the Quickshell plugin system**. It works on a regular Omarchy installation; an Omarchy Kids ISO or fork is not required. The plugin ID is `io.github.peterholko.number-grove`.

![The game running in Qt](preview.png)

## Install

Run these commands in the intended user's Omarchy desktop session:

```bash
omarchy plugin add https://github.com/peterholko/omarchy-number-grove --enable
omarchy-shell shell summon io.github.peterholko.number-grove '{}'
```

## Play

Choose calm or adventure play and a grade from 1–6. Move through the garden and collect answers with Space or Enter. Grades 5 and 6 focus on multiplication and division tables. All questions and scoring run locally. The game does not award screen time.

### Optional app launcher and School Mode

To make the plugin appear in the apps menu and School Mode's app picker, explicitly install its desktop launcher:

```bash
mkdir -p "$HOME/.local/share/applications"
install -m 644 "$HOME/.config/omarchy/plugins/io.github.peterholko.number-grove/io.github.peterholko.number-grove.desktop" "$HOME/.local/share/applications/io.github.peterholko.number-grove.desktop"
```

The launcher has a unique ID. Check before replacing an existing file with that ID if you have customized it. When School Mode is installed, the parent must separately allow the app; installation does not grant school access automatically.

## Dependencies and data

Uses the Quickshell and Qt Quick runtime supplied by Omarchy. The game runs locally; there are no accounts, API keys or network services. The shared practice service is bundled under `service/` and installed only by explicit setup. Its fixed root-owned installed copy verifies game work; the user-writable plugin never runs as root. School-mode status, if available, is read from `/var/lib/omarchy-kids-controls/`; the plugin does not award or remove screen time.

## Update

Version 2.0.0 removes screen-time rewards, their settings and their game transport. Close any open game window before updating:

```bash
omarchy plugin update io.github.peterholko.number-grove
```

If you previously installed a game verifier, also install the shared service update:

```bash
sudo "$HOME/.config/omarchy/plugins/io.github.peterholko.number-grove/setup" --user linnea --upgrade
```

One updated game setup upgrades the shared service for all three games. It retires old pending credits, removes their Screen Time registrations and preserves existing parent limits, completed work, collections, passwords and School Mode settings. Previously awarded minutes are retained. Fresh Number Grove and Paw Post installations need no service setup. Open the games again after updating; a shell restart is not required.

## Remove

If you installed the verifier, run `sudo omarchy-kids-controls remove grove` first. This preserves history and leaves the shared service installed for other games or controls. The service upgrade above removes the former Screen Time registrations while keeping their history.

Remove the optional launcher, if you installed it, then remove the plugin:

```bash
rm -f "$HOME/.local/share/applications/io.github.peterholko.number-grove.desktop"
omarchy plugin remove io.github.peterholko.number-grove
```

## License and source

MIT. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md) for retained copyright notices and asset provenance. [SOURCE.json](SOURCE.json) records the original extraction and current independent integration. This repository is maintained independently; no Omarchy Kids checkout is required.

## Validation

```bash
omarchy plugin validate .
```

These packages are checked with the upstream manifest validator and local source tests. Full desktop enforcement, systemd installation and removal require validation on an actual Omarchy laptop. There are no GitHub Actions workflows in this repository.

Game logic tests (Node.js, development only):

```bash
node --test test/*.cjs
```

Verifier tests (Python 3, development only):

```bash
python3 -m unittest discover -s test -p 'test_*.py'
```

See [service/README.md](service/README.md) for the shared service layout, compatibility and optional integration tests against the real Screen Time ledger. Portable Qt visual tests exercise actual game views, parent limits, collections and compact layouts. Linux service installation still needs a manual check on Omarchy.
