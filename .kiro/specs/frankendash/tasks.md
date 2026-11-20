# Frankendash — tasks

- [x] 1. Kiro account: sign in to Kiro free tier, confirm Kiro user ID
  (needed for the Credit Request Form).
  - Signed in 2026-11-20 via Google (qqqq873451990@gmail.com); `whoami`
    shows the email but no user ID — still to be pulled from the Kiro
    console before filing the form.
- [ ] 2. Create public GitHub repo `frankendash` with MIT license +
  `/.kiro/specs/frankendash/{requirements,design,tasks}.md` copied from
  this draft.
- [x] 3. Verify data sources on the server (read-only inventory; record exact
  endpoints and log paths).
- [x] 4. Backend: `/api/health` + three aggregators (phones / gateway /
  notifications) with timeouts and unknown-on-failure.
- [x] 5. Frontend: one page, three panels, 60 s refresh, status header,
  stitch log, demo login gate.
- [ ] 6. Deploy on the cloud server (port + security group — user approves)
  + public URL smoke test from outside.
- [ ] 7. Demo video (< 3 min, public on YouTube) + Devpost submission
  (new submission, or edit draft 1284018-test — decide before submitting).
- [ ] 8. Credit Request Form by Dec 1, 12:00 PT (Kiro user ID + project
  details). Redeem by Dec 4; credits expire Dec 31.

## Open questions
- Build location: decided — Kiro CLI on the cloud server.
- Repo name: decided — `frankendash`.
- Port number + demo credential: TBD (port needs user approval to open).
- Devpost: new submission or edit draft 1284018-test? TBD.
