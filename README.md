# Number Grove

An arithmetic garden game with calm and adventure play for grades 1–6. Solve a fact, guide your seed courier to the answer, and collect it before the drift bugs catch you.

A standalone community plugin for **Omarchy Quattro with the Quickshell plugin system**, using the ID `io.github.peterholko.number-grove`. It runs on regular Omarchy and needs no background service. Playing never grants or removes screen time.

![Number Grove's grade picker and arithmetic garden](preview.png)

## Install and open

Run these commands in the intended user's Omarchy desktop terminal, without `sudo`:

```bash
omarchy plugin add https://github.com/peterholko/omarchy-number-grove --enable
omarchy-shell shell summon io.github.peterholko.number-grove '{}'
```

## Play

Choose a grade and either **Calm**, with stationary bugs, or **Adventure**, with wandering bugs. A round has ten questions and three hearts. Correct answers earn points and build a streak; mistakes show the correct fact so you can try to remember it next time.

| Grade | Practice |
| --- | --- |
| 1 | Addition and subtraction facts to 20 |
| 2 | Addition, subtraction and the 2–5 multiplication tables |
| 3 | All four operations, with tables through 10 |
| 4 | All four operations, with tables through 12 |
| 5–6 | Multiplication and division tables through 12 |

Use the **arrow keys** or **WASD** to move. Press **Space** or **Enter** while standing on a numbered seed to collect it. **P** or **Escape** pauses the round. The game also pauses when its window loses focus and waits for you to resume.

## Add the app launcher and icon

To show Number Grove in the app launcher and School Mode's app picker, explicitly install its desktop entry and bundled icon:

```bash
mkdir -p "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/512x512/apps"
install -m 644 "$HOME/.config/omarchy/plugins/io.github.peterholko.number-grove/io.github.peterholko.number-grove.desktop" "$HOME/.local/share/applications/io.github.peterholko.number-grove.desktop"
ln -sfn "$HOME/.config/omarchy/plugins/io.github.peterholko.number-grove/assets/launcher.png" "$HOME/.local/share/icons/hicolor/512x512/apps/io.github.peterholko.number-grove.png"
```

The entry and icon use the plugin's unique ID. These commands replace only those named files; preserve any custom versions before running them. The icon link follows future artwork updates.

If [School / Free Time](https://github.com/peterholko/omarchy-school-mode) is installed, a parent must add **Number Grove** to the appropriate approved-app lists. The game reads the existing School Mode status and hides its window when it is not allowed in School Mode. Installing it does not change those lists.

## Dependencies and data

The only runtime dependencies are Omarchy's Quickshell and Qt Quick components. No Python service, privileged setup, account, API key or internet connection is needed to play. Questions and scoring run locally. Round progress lasts for the current game window; closing the game starts a fresh round next time.

When present, School Mode status is read from `/var/lib/omarchy-kids-controls/status/$USER/school-mode/status.json`. No controls configuration is written by this plugin.

## Update

Close the game, then run:

```bash
omarchy plugin update io.github.peterholko.number-grove
```

If you previously installed its launcher, run the launcher commands above again to use the custom icon. If the game still shows an older interface, save your work and log out and back in to clear the shell's cached QML.

Version 2.1 removes the unused shared-service bundle and `setup` command. The game already ran locally in version 2.0. If an earlier installation still has the optional verifier, [remove that legacy enrollment](docs/legacy-service.md); fresh installations need no service commands.

## Remove

Remove the optional launcher and icon, then remove the plugin:

```bash
rm -f "$HOME/.local/share/applications/io.github.peterholko.number-grove.desktop"
rm -f "$HOME/.local/share/icons/hicolor/512x512/apps/io.github.peterholko.number-grove.png"
omarchy plugin remove io.github.peterholko.number-grove
```

For a pre-2.1 verifier installation, also follow the [legacy cleanup instructions](docs/legacy-service.md). Other games and parent controls remain installed.

## License and source

MIT. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md) for copyright notices and artwork provenance. [SOURCE.json](SOURCE.json) records the original extraction and current standalone release. No Omarchy Kids checkout is required.

## Development checks

```bash
omarchy plugin validate .
node --test test/*.cjs
python3 test/visual.py /tmp/number-grove-captures
```

Node.js is needed only for game-logic tests. The visual test requires Python 3 and PySide6, renders the actual Qt Quick game, and exercises Space/Enter collection, grades, complete rounds, mistakes, movement, pause/focus and compact layouts. It writes screenshots outside the checkout. Quickshell window integration and School Mode enforcement still need an Omarchy desktop check. This repository has no GitHub Actions workflows.
