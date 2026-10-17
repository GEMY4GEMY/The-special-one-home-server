"""Windows service wrapper for the local FastAPI server (port 100).

Requires pywin32 and a completed first-run admin bootstrap.
Run from an elevated terminal: python backend/windows_service.py install
"""
import os
import sys
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

class TheSpecialOneService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TheSpecialOneHomeServer"
    _svc_display_name_ = "THE SPECIAL ONE Home Server"
    _svc_description_ = "Local-only student management and exam server on TCP port 100"

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.server:
            self.server.should_exit = True
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        os.chdir(ROOT)
        servicemanager.LogInfoMsg("THE SPECIAL ONE starting on port 100")
        try:
            import uvicorn
            config = uvicorn.Config("backend.app:app", host="0.0.0.0", port=100, log_level="info")
            self.server = uvicorn.Server(config)
            self.server.run()
            if win32event.WaitForSingleObject(self.stop_event, 0) != win32event.WAIT_OBJECT_0:
                raise RuntimeError("Server stopped unexpectedly")
        except Exception as exc:
            servicemanager.LogErrorMsg("THE SPECIAL ONE service failed: " + str(exc))
            raise

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(TheSpecialOneService)
