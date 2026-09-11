# Optional game verification service

This identical 3.0.0 payload is distributed with Pawberry Pet Hotel, Number Grove and Paw Post. Explicit `sudo ./setup --user CHILD --upgrade` installs a root-owned copy under `/usr/lib/omarchy-kids-controls` and loads the selected game module. Adding another game merges the installed module roster. It does not enroll Screen Time or School Mode. Nothing runs as root from the user-writable plugin checkout after setup.

The shared paths preserve existing community Pawberry practice limits and completed counts under `/etc/omarchy-kids-controls` and `/var/lib/omarchy-kids-controls/screen-time/pawberry`. Existing community controls passwords, time/school enrollments and history are retained. Legacy time/school code remains in this payload solely to keep those existing installations working; fresh game setup does not load it. Use the existing controls command explicitly if you want to disable an older enrollment before enabling another screen-time service. Native Omarchy Kids enrollments are refused; setup does not copy or adopt their state.

The installer checks root ownership, command/unit collisions and hashes of the previously installed payload. Different payloads cannot claim the same version. Local modifications and downgrades stop the upgrade for review. Shared service upgrades require `--upgrade`. All game releases carrying this service version must bundle exactly the same payload. A newer game service should not be overwritten by an older combined-controls setup.

## Verification and credits

The Unix socket supplies the child's UID. Game requests cannot choose a different user or grant minutes. Grove issues arithmetic questions, Pawberry issues operands and checks the entire column-work sequence, and Paw Post issues text and checks a bounded sequence of in-game keys, accuracy and basic timing. These checks reject a bare final answer or self-reported score as a credit request. They are supervised practice checks, not proof of human input against a child who writes an automated solver. Paw Post records no keys outside its game window; its submitted input sequence is not persisted.

A verified completion receives a durable receipt before the root-only `omarchy-peterholko-screen-time-credit` helper is called. The helper receives no reward amount. The platform owns account enrollment, parent password/PIN authentication, enabled providers, seconds per completion, provider caps and the global cap. Its accepted amount, including a partial or zero award, is authoritative. The same receipt/day is retried after uncertain responses and service restarts, and deferred acknowledgements appear in game status. Work runs outside the shared accounting lock. Pending queues are bounded; an exhausted queue accepts ordinary game completion with zero time. Receipts cannot be regenerated under a new day to recover yesterday's credit.

Pawberry pins each problem and pending credit to its selected backend. Existing settings without a backend retain the old combined-controls integration. New enrollments select the new platform with participation off. Parent daily-limit edits never reset completion counts. Removing Pawberry integration switches participation off while retaining practice settings and history.

The systemd service only needs additional write access to the platform's state and runtime directories to invoke its root helper. It does not write the platform's configuration at runtime. Explicit setup registers providers through the platform admin command if installed, without enabling rewards or changing rates/caps. If the platform is installed later, rerun game setup to register providers and refresh the service sandbox.

## Local checks

Run `python3 -m unittest discover -s test -p 'test_*.py'` from a game checkout. Optional integration tests exercise the actual platform source without installing it: set `SCREEN_TIME_PLATFORM_SOURCE=/path/to/omarchy-screen-time-platform` for the same command. All state stays in temporary directories. The tests do not invoke systemd, PAM, sudo, GitHub Actions, or an ISO.
