# LiteTube 🎵

### A lightweight Windows desktop music player powered by YouTube audio.

**LiteTube** is a fast, privacy-friendly, audio-only YouTube music player for Windows. Search for music, play it in a clean desktop window, build playlists, manage your queue, and enjoy your music without loading unnecessary video.

No heavy streaming interface. No video playback. Just the music.

---

## ✨ Why LiteTube?

Streaming music can use a lot of data when you're loading video, thumbnails, animations, comments, and other unnecessary content.

LiteTube takes a simpler approach:

> **Search → Play → Listen.**

LiteTube focuses on the audio experience so you can enjoy music while using less bandwidth than full video playback.

### With LiteTube you can:

- 🎵 Search YouTube for music
- 🔊 Play audio without opening the YouTube website
- 💾 Reduce unnecessary video data usage
- 📋 Create and manage local playlists
- ⏭️ Build and reorder your playback queue
- 🔀 Shuffle your music
- 🔁 Repeat tracks
- 🕘 Keep playback history
- 🔗 Play music from supported YouTube URLs
- 🌙 Use Light or Dark mode
- 🖥️ Use LiteTube as a standalone Windows application
- 🔄 Receive notifications when a new LiteTube version is available

---

# 🖥️ A Real Windows Desktop App

LiteTube is designed to run as its own Windows application.

You don't need to keep a browser tab open just to use the player.

After building the application:

```text
LiteTube.exe
```

opens LiteTube inside its own resizable Windows window.

The desktop shell uses WebView2/pywebview while Flask runs locally as the application backend.

---

# 🎧 Audio-Only Music Experience

LiteTube is designed around listening rather than watching.

Instead of loading a complete video experience, LiteTube focuses on the audio stream.

This can help reduce unnecessary bandwidth usage, especially when you are listening for long periods.

### Why audio-only?

When you're listening to music, you may not need:

- Video playback
- Large video frames
- YouTube's full website interface
- Comments
- Recommended video feeds
- Unnecessary page elements

LiteTube keeps the experience focused on the thing that matters:

**Your music.**

> Actual data usage depends on the selected audio format, source, network conditions, and YouTube content.

---

# 💰 Save Your Data

If you're listening to music rather than watching videos, downloading and processing video is often unnecessary.

LiteTube is built to keep playback focused on audio.

That means LiteTube can be useful when:

- You have limited bandwidth
- You're using mobile hotspot data
- You want a lightweight music player
- You don't need video while listening
- You want to keep your music library and queue locally

---

# 🎶 Do I Need Spotify Premium?

LiteTube does **not require a Spotify subscription** to use LiteTube.

LiteTube is a separate Windows music player that uses supported YouTube audio sources.

You can search for music and listen through LiteTube without paying for a LiteTube subscription.

### Important

LiteTube does not provide or sell music licenses.

You are responsible for using content that you are legally authorized to access and play in your region.

---

# 🚫 No Extra Ads From LiteTube

LiteTube does not add its own advertising layer to the player interface.

There are no LiteTube banner ads, pop-up advertisements, or sponsored playlists built into the application.

However, LiteTube does not control the availability, advertising, licensing, or policies of third-party content sources.

---

# 📋 Playlists

Create local playlists to organize your music.

You can:

- Create playlists
- Add songs
- Remove songs
- Play individual tracks
- Play an entire playlist
- Start playback from a specific song
- Reorder playlist tracks

Your playlists are stored locally for your LiteTube app origin.

---

# ⏭️ Smart Queue

LiteTube includes a flexible playback queue.

You can:

- Add tracks to the queue
- Remove tracks
- Drag and reorder tracks
- Start playback from any queued song
- Shuffle playback
- Use repeat controls
- Continue with recommendations when the queue is empty

The queue is designed to make LiteTube feel like a dedicated music player rather than a simple YouTube search page.

---

# 🕘 Playback History

LiteTube keeps recent playback history locally so you can move back through recently played tracks.

History helps with:

- Previous track navigation
- Finding recently played music
- Returning to songs you listened to earlier

---

# 🌙 Light & Dark Mode

LiteTube includes a modern glass-style interface with Light and Dark themes.

The interface is designed to remain clean and comfortable during long listening sessions.

---

# 🔄 Automatic Updates

LiteTube can check the project's GitHub Releases for newer versions.

When a new version is published, the application can notify the user and provide a link to the latest release.

Example:

```text
v1.0.0
   ↓
v1.1.0
   ↓
LiteTube detects the new release
   ↓
User receives an update notification
```

Updates are distributed through GitHub Releases.

---

# 🛠️ Build LiteTube for Windows

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- Internet connection
- Microsoft Edge WebView2 Runtime

Python must be available through the `python` command.

---

## 1. Install Python

Install Python 3.10+ and enable:

```text
Add Python to PATH
```

Verify:

```bat
python --version
```

---

## 2. Build the Windows application

Run:

```text
build_windows_desktop.bat
```

The build script creates the required virtual environment, installs dependencies, and builds the Windows executable.

After the build completes:

```text
LiteTube.exe
```

will be created.

---

## 3. Launch LiteTube

Double-click:

```text
LiteTube.exe
```

LiteTube should open as a standalone Windows application.

The main interface does not need Chrome or Edge.

---

# 🌐 Development Version

Developers can also run the Flask source version.

Run:

```text
run.bat
```

The development version opens the local LiteTube web interface in your browser.

This mode is intended for development and testing.

For normal Windows users, use:

```text
LiteTube.exe
```

---

# 🌍 WebView2 Requirement

The desktop application uses Microsoft's Edge WebView2 runtime.

Most modern Windows 10 and Windows 11 installations already include WebView2.

If LiteTube reports that WebView2 is missing, install the official Microsoft WebView2 Runtime and run the build again.

---

# 🔄 GitHub Release System

LiteTube uses GitHub Releases for version distribution.

The repository is configured through:

```text
update_config.json
```

Example:

```json
{
  "github_repo": "uploopcloud/LiteTube",
  "release_channel": "stable",
  "check_on_start": true
}
```

Create releases using version tags such as:

```text
v1.0.0
v1.1.0
v1.2.0
```

The application can compare its installed version with the latest GitHub release.

---

# 💾 User Data & Playlists

LiteTube currently stores playlists and related interface state in the local storage associated with the LiteTube app origin.

Replacing the application executable does not intentionally delete this data.

### Important

Do not clear LiteTube's WebView/browser site storage if you want to keep locally stored playlists and settings.

A future installer version may move persistent user data to:

```text
%APPDATA%\LiteTube
```

for stronger upgrade and migration safety.

---

# 🔒 Privacy

LiteTube is designed as a lightweight local application.

The LiteTube backend runs locally on your Windows computer.

LiteTube does not require a LiteTube account to create local playlists or use the player.

Network requests may be made to third-party services required for search, audio extraction, playback, updates, or other application functionality.

Review and follow the terms and policies of the services and content sources you use.

---

# ⚖️ Content & Copyright

LiteTube is a player/interface and does not own or distribute the music available through third-party sources.

Only access, download, or play content when you have the necessary rights or permission to do so.

Users are responsible for complying with applicable copyright laws, YouTube's terms, and the terms of any third-party service they use.

---

# 🚀 Roadmap

Potential future improvements include:

- [ ] Improved Windows installer
- [ ] Persistent user data in `%APPDATA%\LiteTube`
- [ ] More playback controls
- [ ] Better playlist management
- [ ] Improved download/data usage controls
- [ ] Additional desktop integrations
- [ ] More reliable automatic update workflow
- [ ] Additional audio quality options

---

# 🤝 Contributing

Contributions, bug reports, feature ideas, and improvements are welcome.

If you find a problem, open an issue with:

1. Windows version
2. LiteTube version
3. Steps to reproduce the problem
4. Error message or screenshot
5. Relevant logs if available

---

# 📜 License

See the repository license file for the applicable license and usage terms.

---

## ⭐ LiteTube

**Search less. Watch less. Listen more.**

A lightweight YouTube-powered audio player for Windows.

🎵 **Music**

🖥️ **Windows Desktop**

💾 **Data-conscious playback**

📋 **Local Playlists**

⏭️ **Smart Queue**

🌙 **Light & Dark Mode**

🔄 **GitHub Updates**

---

> LiteTube is an independent project and is not affiliated with YouTube, Google, Spotify, Microsoft, or any music label or rights holder.