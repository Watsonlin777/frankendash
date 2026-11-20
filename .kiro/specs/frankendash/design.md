# Frankendash — design

### Stack (default, changeable during build)
- Backend: Python 3 stdlib-only HTTP server (zero dependencies, runs anywhere).
- Frontend: static HTML/JS, no build step, auto-refresh every 60 s.
- Hosting: the owner's cloud server, one port; opening the port in the
  security group needs the owner's approval. The server address is configured
  at deploy time and never committed to the repo.

### Backend API (all GET, read-only)
- `/api/health` — service up, per-source reachability.
- `/api/phones` — A/B: tunnel, adb, services, location age.
- `/api/gateway` — providers, routing order, usage/burn.
- `/api/notifications` — recent WeCom pushes.
- Server-side cache 60 s; 5 s timeout per source; source failure yields
  "unknown" with last-good time, never fabricated data.

### Data sources (verify read-only on the server before coding)
- Phones: tunnel listeners 2222/2223, `adb devices` 18091/18092, Termux
  status server via tunnel (`127.0.0.1:18123/status`), newest file in
  `/root/life/raw/`, `/root/life/location_watch_state.json`,
  `/root/life/phones/` configs.
- Gateway: `http://127.0.0.1:3425/v1/models`, Magpie usage
  (`magpie usage --csv today` or the usage log), provider list.
- Notifications: server logs of WeCom sends — water reminder script runs,
  stock monitor log, watchdog logs (exact paths to confirm on server).

### UI
- Header: overall status (ok / degraded / down) + last refresh time.
- Three panels (Phones / Gateway / Notifications) + stitch-log footer.
- Readable on a phone screen (the owner checks from his phone).

### Privacy + access
- Aggregation only; redact everything listed in R5.
- Demo login gate (one demo credential, given to judges only via the
  Devpost form; never the real webhook or any real credential).
