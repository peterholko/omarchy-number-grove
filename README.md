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

### Optional app launcher and School Mode

To make the plugin appear in the apps menu and School Mode's app picker, explicitly install its desktop launcher:

```bash
mkdir -p "$HOME/.local/share/applications"
install -m 644 "$HOME/.config/omarchy/plugins/io.github.peterholko.number-grove/io.github.peterholko.number-grove.desktop" "$HOME/.local/share/applications/io.github.peterholko.number-grove.desktop"
```

The launcher has a unique ID. Check before replacing an existing file with that ID if you have customized it. When School Mode is installed, the parent must separately allow the app; installation does not grant school access automatically.

## Dependencies and data

Uses the Quickshell and Qt Quick runtime supplied by Omarchy. The game runs locally; there are no accounts, API keys or network services. The optional controls service is not bundled with this plugin. School-mode status, if available, is read from `/var/lib/omarchy-kids-controls/`; the plugin does not write root-owned settings or reward totals.

## Update

```bash
omarchy plugin update io.github.peterholko.number-grove
```

## Remove

Remove the optional launcher, if you installed it, then remove the plugin:

```bash
rm -f "$HOME/.local/share/applications/io.github.peterholko.number-grove.desktop"
omarchy plugin remove io.github.peterholko.number-grove
```

## License and source

MIT. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md) for retained copyright notices and asset provenance. [SOURCE.json](SOURCE.json) records the source revision and reproducible exporter in [Omarchy Kids](https://github.com/peterholko/omarchy-kids).

## Validation

```bash
omarchy plugin validate .
```

These packages are checked with the upstream manifest validator and local source tests. Full desktop enforcement, systemd installation and removal require validation on an actual Omarchy laptop. There are no GitHub Actions workflows in this repository.

Game logic tests (Node.js, development only):

```bash
node --test test/*.cjs
```
