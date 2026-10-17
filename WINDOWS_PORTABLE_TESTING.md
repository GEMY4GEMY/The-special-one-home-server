# THE SPECIAL ONE — Windows x64 offline test build

The Windows GitHub Actions workflow builds a **portable test package**, not an installer.

## Download

Open [Windows portable workflow](https://github.com/GEMY4GEMY/The-special-one-home-server/actions/workflows/windows-portable.yml), select a **successful** run, and download the artifact named `TheSpecialOne-Windows-x64-Portable`. A GitHub sign-in may be required.

The artifact contains multiple `.7z.001`, `.7z.002`, ... parts. **Keep all parts together**. Use a 7z-compatible extractor to extract starting with `.7z.001`. Windows 11 support for split archives varies; an extractor may be needed on the target computer. The extracted application itself does not require installing Python or Ollama.

## Start

1. Extract the complete `dist/TheSpecialOne` folder to a writable location.
2. Double-click `START_PORTABLE_WINDOWS.bat`.
3. On first launch choose an administrator password of at least 12 characters.
4. Open `http://localhost:100/` and sign in as `Mrsameh`.

The server listens on port 100 for local-network tablets. Windows Firewall may require a one-time permission prompt. The offline model is `qwen3-vl:4b` and must be present under `ai-models`.

## Limitations

- No claim is made that a build has succeeded until the GitHub Actions job is green and the archive is downloaded and tested on a Windows PC.
- AI output must be reviewed by the teacher. Model accuracy on scanned books and curricula has not yet been established.
- The portable launch is not a Windows auto-start service; keep the launcher running during exams.
- Preserve the `backend/data` folder when updating the program; it holds the SQLite database.
