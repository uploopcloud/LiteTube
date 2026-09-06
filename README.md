# LiteTube — Windows Release-Ready Build

LiteTube is a local Windows audio-only music player powered by Flask and yt-dlp.

## Run from source

1. Install Python 3.10+ and make sure `python` works in CMD.
2. Double-click `run.bat`.
3. The app opens at `http://127.0.0.1:8000`.

## Build the Windows EXE

On Windows, double-click `build_windows_desktop.bat`. It builds `LiteTube.exe` with PyInstaller and embeds the LiteTube icon. Python is only needed on the build machine; the resulting EXE contains the Python runtime.

## Versioning and GitHub updates

- Current version is in `VERSION.txt`.
- Before publishing, change `update_config.json` from `YOUR_GITHUB_USERNAME/LiteTube` to your real GitHub repository, for example `myname/LiteTube`.
- Create GitHub Releases such as `v1.0.0`, `v1.1.0`, etc.
- LiteTube checks GitHub for a newer release when it starts and has a **Check for updates** button.
- Update notifications open the GitHub release page so the user can download/install the new Windows build.

## Playlist safety

Playlists, queue, quality and theme are stored in the local browser profile used by LiteTube. Replacing `LiteTube.exe` does not intentionally delete them. The updater/release process should never delete the user's browser profile or app-data folder.

For a future installer, keep user data outside the installation directory so uninstall/update operations cannot remove it.
