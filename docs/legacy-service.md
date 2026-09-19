# Retire the old Number Grove verifier

This applies only if you explicitly installed the optional verifier with an earlier Number Grove release. Version 2.1 no longer bundles a service or a `setup` command. Ordinary gameplay is entirely local.

Use the existing installed admin command to remove Number Grove's old verifier enrollment:

```bash
sudo omarchy-kids-controls remove grove
```

This removes that verifier for its enrolled accounts, retains its history and keeps the shared service for any other installed modules, including Pawberry parent limits and School Mode. It does not delete their configuration. If the command is absent, no standalone shared verifier is installed; do not install one for this game.

If you also used the separate Screen Time platform and its admin command is still installed, remove only Number Grove's old provider registration:

```bash
sudo omarchy-peterholko-screen-time-admin provider-remove peterholko.number-grove
```

Previously credited time and history remain. The current game cannot submit time rewards. Do not run setup from an old game checkout to enable it again.
