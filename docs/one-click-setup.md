# One-click launcher

Double-click **START_THE_SPECIAL_ONE.bat** from the project directory.

The launcher:
1. Requests Windows administrator permission.
2. Detects an already-installed service and starts it if necessary.
3. On first use, creates the Python environment and installs dependencies (requires Python and Internet for initial package installation).
4. Asks for a **new** administrator password in a hidden prompt. It is not stored in a GitHub file.
5. Initializes the local database.
6. Registers the Windows service with automatic startup and crash recovery.
7. Opens http://localhost:100/.

**Important:** This is an automated *source-code setup launcher*, not yet a standalone EXE installer. It still requires Python and Internet for initial dependency installation. Windows service behavior remains untested on the target PC. Do not use real student data until security hardening is complete.

A future Windows EXE installer will bundle the runtime and dependencies, removing the Python prerequisite. Windows administrator permission remains necessary for installing a system service.

No real passwords, database files, or student records should ever be committed to GitHub.
