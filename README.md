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

Choose calm or adventure play and a grade from 1–6. Move through the garden and collect answers with Space or Enter. Grades 5 and 6 focus on multiplication and division tables. Optional time rewards use the separately installed Screen Time service; ordinary play is fully standalone.

### Optional Screen Time rewards

Use the separate [Screen Time platform](https://github.com/peterholko/omarchy-screen-time-platform), programmatic ID `peterholko.screen-time`. Install and enroll it for the child first. Review this game's `service/` payload, then explicitly install its verifier from the child's Omarchy desktop terminal:

```bash
omarchy plugin update io.github.peterholko.number-grove
sudo "$HOME/.config/omarchy/plugins/io.github.peterholko.number-grove/setup" --user linnea --upgrade
```

Replace `linnea` with the intended local account. Fresh setup enables only this game verifier. It does not enroll School Mode or the older screen-time clock. The three games share one service; installing another merges its module registration and preserves existing community controls passwords, settings and Pawberry practice counts. If Screen Time was installed later, rerun game setup to register the provider and refresh the service sandbox.

Setup registers `peterholko.number-grove` with rewards off. Open **Screen Time · Parents → Connected games**, enable the overall rewards switch and this game, then choose seconds per completion, its daily cap and the overall cap. Changes require Screen Time's parent password, or its optional enabled PIN. Registration and game updates preserve those choices.

Choose **Play & earn time** to participate. The game service generates the question for the selected grade and checks the collected answer. Each correct answer is one completion; the platform decides the credited amount, including a partial award near a cap. Replayed answers cannot earn twice. The round displays confirmed credits and updates when a delayed acknowledgement arrives. Practice mode always works without either service.

### Optional app launcher and School Mode

To make the plugin appear in the apps menu and School Mode's app picker, explicitly install its desktop launcher:

```bash
mkdir -p "$HOME/.local/share/applications"
install -m 644 "$HOME/.config/omarchy/plugins/io.github.peterholko.number-grove/io.github.peterholko.number-grove.desktop" "$HOME/.local/share/applications/io.github.peterholko.number-grove.desktop"
```

The launcher has a unique ID. Check before replacing an existing file with that ID if you have customized it. When School Mode is installed, the parent must separately allow the app; installation does not grant school access automatically.

## Dependencies and data

Uses the Quickshell and Qt Quick runtime supplied by Omarchy. The game runs locally; there are no accounts, API keys or network services. The optional verifier is bundled under `service/` and installed only by explicit setup. Its fixed root-owned installed copy verifies game work; the user-writable plugin never runs as root. School-mode status, if available, is read from `/var/lib/omarchy-kids-controls/`; the plugin does not write root-owned settings or reward totals.

## Update

The bundled shared service 3.0.1 fixes status-file permission failures that can leave the School / Free Time launcher showing only Style. Install this fix with both the plugin update and the service setup below, then run `omarchy restart shell`. Saved parent settings, app approvals, schedules and game progress are retained.

```bash
omarchy plugin update io.github.peterholko.number-grove
```

When using optional rewards or parent practice limits, also review and update the bundled verifier:

```bash
sudo "$HOME/.config/omarchy/plugins/io.github.peterholko.number-grove/setup" --user linnea --upgrade
```

## Remove

If you installed the verifier, run `sudo omarchy-kids-controls remove grove` first. This preserves history and leaves the shared service installed for other games or controls. To remove the provider from Screen Time, explicitly run `sudo omarchy-peterholko-screen-time-admin provider-remove peterholko.number-grove`; its daily credit history is retained.

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

See [service/README.md](service/README.md) for the shared service layout, compatibility and optional integration tests against the real Screen Time ledger. Portable Qt visual tests exercise actual game views, including reward delays and compact layouts. Linux service installation still needs a manual check on Omarchy.
