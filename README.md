# Frankendash

A read-only Mission Control dashboard, built with [Kiro](https://kiro.dev) for
Kiroween 2026. It stitches three systems that were never designed to talk to
each other onto one screen:

- **Phones** — phone A and B status over reverse-SSH tunnel + ADB (tunnel,
  adb, Termux services, location-data age).
- **Gateway** — Magpie gateway provider health, group/group routing order,
  today's usage and burn against the caps.
- **Notifications** — recent WeCom pushes (water reminders, stock alerts,
  watchdog alerts).

A footer "stitch log" shows, per panel, which transport the data came over
and when it was last fetched. That stitching is the point: three incompatible
systems, one screen.

Read-only: the dashboard never sends commands to phones, the gateway, or
WeCom. No coordinates, IPs, phone numbers, webhook URLs, keys, or tokens ever
appear in the UI, API responses, or logs.

## Run

Python 3, standard library only, no dependencies:

```
python3 server.py
```

## Spec

The build spec lives in `.kiro/specs/frankendash/` (requirements, design,
tasks). License: MIT.
