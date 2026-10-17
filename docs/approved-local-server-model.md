# Approved server model — aligned with Ultrasound Booking System

Reference: https://github.com/GEMY4GEMY/Ultrasound-Booking-System

THE SPECIAL ONE is a **local LAN web server**, NOT a packaged desktop EXE and NOT a Railway deployment.

## Operating model
- The main Windows computer runs the server as a background service.
- Students, teachers, and admins use a browser on Android tablets or computers.
- Base address: `http://<server-LAN-IP>:100/`.
- No Android app installation or internet connection is needed for routine LAN operation.
- Port: 100 (fixed as requested).
- Local-only student data; authenticated students may access only their own results.
- Auto-start at boot, service crash recovery, health checks, and browser reconnect.
- A single first-run setup/launcher **inside the repository** may install the Windows service; this is not an EXE application and should not require users to run multiple manual commands.

## Reference implementation pattern
The Ultrasound Booking System repository includes source server code, LAN setup instructions, auto-start scripts, and a server watchdog. THE SPECIAL ONE will follow the same deployment concept, while keeping its exam/student-specific backend and user interface.

## Current development state
- Initial Python/FastAPI web server code is committed.
- A Windows service wrapper and integrated setup script are committed.
- The server and service have not yet been verified on the user's Windows hardware.
- Offline answer synchronization, HTTPS, rate limits, and production-ready student privacy controls are pending.
- Do not enter real student records until hardening and validation are completed.
