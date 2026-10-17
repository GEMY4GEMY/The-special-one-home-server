# Windows auto-start and recovery

This is a **prototype** service. Do not load real student data yet.

1. Install Python 3.11+ on the Windows server.
2. In PowerShell from repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install pywin32
$env:TSO_ADMIN_USERNAME = 'Mrsameh'
$env:TSO_ADMIN_INITIAL_PASSWORD = Read-Host 'Enter a NEW private admin password'
.\scripts\start-server.bat
```

3. Wait until the app starts, visit `http://localhost:100/health`, then stop the interactive server with Ctrl+C. Remove the temporary secret from the terminal environment with `Remove-Item Env:TSO_ADMIN_INITIAL_PASSWORD`.
4. Open **PowerShell as Administrator** and run `.\scripts\install-windows-service.ps1`.
5. Check with `.\scripts\service-status.ps1`. Reboot and check again.

Service name: `TheSpecialOneHomeServer`. Automatic startup at boot; Service Control Manager restarts after unexpected failures with 5, 10, and 30 second delays.

## Network
- Windows Firewall: allow inbound TCP **100** only on **Private** network profiles.
- Assign the Windows server a reserved IP in the router.
- Android URL: `http://SERVER-IP:100`.
- Never configure router port forwarding for port 100.

## Important limitations
- Service installation and reboot behavior have not yet been verified on an actual Windows PC.
- Reconnect/offline answer synchronization has not yet been implemented.
- Existing HTTP and in-memory sessions are not production hardened; HTTPS, rate limiting, CSRF protections, backups, and security testing remain required.
- Initial prototype uses SQLite, not PostgreSQL.
- On Windows, binding to TCP port 100 may require elevated privileges or security-policy adjustments; verify local policies and firewall rules.
