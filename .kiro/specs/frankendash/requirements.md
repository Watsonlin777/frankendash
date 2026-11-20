# Frankendash — requirements

Frankendash is a one-page, read-only Mission Control dashboard that stitches
three systems never designed to talk to each other: phone A/B status, Magpie
gateway health and usage, and recent WeCom notifications. The Frankenstein
story is the stitching itself: each panel crosses a different transport
(reverse SSH / HTTP gateway API / webhook logs), and a footer "stitch log"
shows exactly how each panel got its data.

All code is written fresh inside the Submission Period (Oct 30 – Dec 4, 2026).
The dashboard only reads existing local endpoints and logs; no existing code
is copied. Any snippet reused from earlier work must be disclosed here before
submission.

### R1 — Phones panel
As the owner, I can see phone A (PHB110) and phone B (PJZ110) status on one
screen: tunnel up/down, adb online/offline, Termux services
(trigger/collector/collect/sync) running or not, and location-data age.
- WHEN a phone's newest location sample is older than 2 hours, THEN the panel
  flags it stale with the last-good timestamp.
- WHEN a source cannot be reached, THEN the panel shows "unknown", never a
  guessed value.

### R2 — Gateway panel
As the owner, I can see Magpie gateway health: provider list with up/down,
the group/group routing order and classifier, and today's usage plus burn
against the known caps.
- WHEN a provider check fails, THEN it shows down with the check time.
- WHEN usage data is unavailable, THEN the panel shows "unknown", never 0.

### R3 — Notifications panel
As the owner, I can see the most recent WeCom pushes with time, text, and
which script sent them (water reminder / stock monitor / watchdog), plus
delivery status where the server logs record it.

### R4 — Public URL + demo login for judges
As a judge, I can open the public URL, log in with the demo credential
supplied in the Devpost submission form, and see the live dashboard.
- WHEN no demo credential is supplied, THEN the app shows the login page
  only, no data.

### R5 — Privacy
No coordinates, IPs, phone numbers, webhook URLs, keys, or tokens appear
anywhere in the UI, API responses, or logs.

### R6 — Read-only
The dashboard issues no commands to phones, gateway, or WeCom: no restarts,
no deletes, no sends. It is observability only.

### R7 — Stitch log
The footer lists, per panel: transport used, last fetch time, fetch status.
This is the demo story: three incompatible systems, one screen.

### R8 — Repo
Public GitHub repo, MIT license, `/.kiro` at the root with
`specs/frankendash/{requirements,design,tasks}.md`, steering, and hooks.
The repo contains everything needed to run the app.
