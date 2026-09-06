# LiteTube

A polished Windows desktop YouTube-powered audio-only music player.

## What this build does

- **Standalone Windows desktop app** — the main UI opens inside its own LiteTube window.
- Does **not** open Chrome/Edge as the main interface.
- Uses Flask locally for the backend and WebView2/pywebview for the desktop window.
- Search, suggestions, direct YouTube URLs, normal playlists, queue, shuffle/repeat, history and local playlists.
- Glass light/dark interface.
- GitHub release update checker.

## Build the Windows app

1. Install Python 3.10+ and enable **Add Python to PATH**.
2. Double-click `build_windows_desktop.bat`.
3. Wait for the build to finish.
4. Your app will be created as:

```text
LiteTube.exe
```

Double-click `LiteTube.exe`. LiteTube should open as a normal resizable Windows application window.

### WebView2 requirement

The desktop shell uses Microsoft's Edge WebView2 runtime. Most modern Windows 10/11 systems already include it. If Windows reports that WebView2 is missing, install the official Microsoft Edge WebView2 Runtime and run the build again.

## Run source version

`run.bat` starts Flask and opens the local web version in your browser. This is only for development/testing; the Windows release should use `LiteTube.exe`.

## GitHub updates

`update_config.json` contains the GitHub repository used by the in-app update checker. Replace the placeholder repository with your real repository, for example:

```json
{
  "github_repo": "YOUR_USERNAME/LiteTube",
  "release_channel": "stable",
  "check_on_start": true
}
```

Create GitHub Releases such as `v1.0.0`, `v1.1.0`, etc. The app can detect a newer release and open its GitHub release page.

## User data

LiteTube playlists and related UI state are currently stored in the browser/WebView local storage for the app origin. Replacing the EXE does not intentionally clear that storage. Do not clear LiteTube site/app storage if you want to preserve local playlists.

For a future installer, user data should be moved to `%APPDATA%\\LiteTube` for stronger upgrade safety.

Use only content you are authorized to access and play.
