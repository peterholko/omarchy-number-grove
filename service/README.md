# Shared practice service

This identical 4.0.0 payload is bundled with Pawberry Pet Hotel, Number Grove and Paw Post. Explicit setup installs a root-owned copy under `/usr/lib/omarchy-kids-controls`. Fresh Pawberry setup supports its parent-protected daily practice limits. Number Grove and Paw Post run locally without this service; their older verification endpoints remain compatible for existing installations and always return zero time.

## Upgrading from time rewards

Run `sudo ./setup --user CHILD --upgrade` from one updated game checkout. The upgrade removes both the separate Screen Time adapter and the older combined-controls reward adapter. Pending credits are retired without submission, including after a restart. Already recorded screen-time balances and history are retained. Setup unregisters only `peterholko.pawberry`, `peterholko.number-grove` and `peterholko.paw-post` through the installed Screen Time admin command, if present. No game can register or enable time rewards again.

Pawberry's parent settings now contain only daily practice limits. The service removes obsolete reward preferences while keeping addition, subtraction and multiplication limits, counts and unfinished problems. Collections and accessories live in the user's separate collection file and are untouched. The updated game waits for a service that confirms `practice_only: true` before sending work, so an old backend cannot silently award time during a partial upgrade.

## Existing controls and verification

The shared paths preserve existing community settings under `/etc/omarchy-kids-controls` and `/var/lib/omarchy-kids-controls`. Existing parent passwords, time/school enrollments, approved apps, schedules and history are retained. Legacy time/school code remains solely to keep those existing installations working; fresh game setup does not enroll either clock or School Mode. Native Omarchy Kids enrollments are refused rather than adopted.

The installer checks ownership, command/unit collisions and hashes of the previously installed payload. Local modifications, differing payloads with the same version, and downgrades stop the upgrade. All game releases carrying this service version bundle exactly the same payload. Do not overwrite it with an older controls setup.

The Unix socket determines the child's UID. Pawberry issues operands, verifies each intermediate step, and commits a completion before awarding its pet. Wrong answers, incomplete work and retries cannot consume extra daily slots. Limits require the controls parent password and never reset completed counts. The compatibility verifiers for Grove and Paw Post retain challenge validation without any path to screen-time accounting. The runtime no longer has write access to the separate Screen Time platform's directories.

## Local checks

Run `python3 -m unittest discover -s test -p 'test_*.py'` from a game checkout. Set `SCREEN_TIME_PLATFORM_SOURCE=/path/to/omarchy-screen-time-platform` to also prove that completions and old pending receipts leave its actual ledger unchanged. All state is temporary. The tests do not run systemd, PAM, sudo, GitHub Actions or an ISO. Linux installation still needs a manual check on Omarchy.
