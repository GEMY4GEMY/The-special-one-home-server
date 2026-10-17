# Phase 1 — Approved Requirements

- Deployment: Windows LAN server only; no cloud service.
- Clients: 5–10 Android tablets over local Wi-Fi.
- Grades: primary, preparatory and secondary.
- Auto-start: Windows service at boot, before user sign-in.
- Recovery: restart service on failure; health check endpoint.
- Reconnect: tablet automatically detects return of connectivity.
- Data durability: queue pending exam answers locally; synchronize with idempotent request IDs.
- Access control: student can only read their own records and published results.
- Staff access scoped to explicitly authorized classes and groups.
- Permanent student identifier; longitudinal academic history.
- Encrypted backups and tested restore procedure before production.
- Never publish real student data to GitHub.
