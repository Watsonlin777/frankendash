# Privacy

- No coordinates, IPs, phone numbers, webhook URLs, keys, or tokens anywhere
  in the UI, API responses, logs, or this repo.
- The server address and any credential are configured at deploy time and
  never committed.
- When a source cannot be reached, show "unknown" with the last-good time —
  never a guessed value, never 0.
