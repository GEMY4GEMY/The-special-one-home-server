# Local server installation — Windows

**Prototype only. Do not enter real student records yet.**

## Prerequisites
- Python 3.11 or newer
- Windows PC connected to the same LAN/Wi-Fi as Android tablets

## First run (PowerShell)
```powershell
cd C:\path\to\The-special-one-home-server
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:TSO_ADMIN_USERNAME = "Mrsameh"
$env:TSO_ADMIN_INITIAL_PASSWORD = Read-Host "Set initial admin password"
.\scripts\start-server.bat
```

The password must be entered **only on the local PC**, never in GitHub or screenshots. The admin is created on first start with an Argon2 password hash. Existing passwords are not overwritten on subsequent starts.

## LAN access
- Server health: http://localhost:100/health
- Login: http://SERVER-LAN-IP:100/
- Allow inbound TCP port 100 on Windows Firewall **for Private networks only**.
- Give the server PC a DHCP reservation so its IP does not change.
- Do not forward port 100 from the router to the Internet.

## Limitations
- Session storage is currently in memory; restarting the process logs users out.
- This initial version uses HTTP on the LAN; deploy TLS before storing real student information.
- The current SQLite storage is a prototype; PostgreSQL, audit logging, robust backups and offline answer synchronization are pending.
- Windows service auto-start and crash recovery are not yet implemented.
- Login rate limiting, password reset, CSRF hardening and production security testing are pending.
- Avoid using real student data until all security requirements are completed.
