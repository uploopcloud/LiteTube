# LiteTube

### A Lightweight, Premium Music Player for Windows

LiteTube is a lightweight Windows desktop music player designed for a clean, focused music listening and discovery experience powered by YouTube's music ecosystem.

It combines a modern glassmorphism interface with music discovery, smart search, playlists, queue management, playback history, and location-based music suggestions — all inside a lightweight desktop application.

---

## ✨ Features

### 🎵 Music Discovery

- Location-based music discovery
- Detects approximate user location using public IP
- Suggests artists based on location
- Suggests songs based on location
- Music-focused recommendations
- Music filtering to reduce non-music content
- No YouTube Data API key required
- No YouTube Home recommendation scraping
- No browser window required for normal operation

---

### 🔎 Smart Music Search

Search YouTube for:

- Songs
- Artists
- Albums
- Music videos
- Other music-related content

Search results use the same music-focused filtering system to reduce unwanted non-music results.

Search suggestions are provided while typing.

Playing a search result does **not** automatically add every search result to the queue.

---

## ▶️ Music Player

LiteTube includes a dedicated audio-focused player with:

- Play
- Pause
- Previous
- Next
- Seek
- Progress tracking
- Volume control
- Current track information
- Automatic playback continuation
- Queue-aware playback

When a queue exists, queued tracks take priority.

When the queue is empty, LiteTube can continue playback through available music suggestions.

---

## 📋 Queue

The queue system supports:

- Add songs to queue
- Remove songs from queue
- Drag-and-drop reordering
- Magnetic reordering
- Visual drag placeholder
- Queue priority during playback
- Automatic removal of completed queue tracks

Songs can be moved directly to another position using drag-and-drop.

For example:

```text
Song 1
Song 2
Song 3
Song 4
Song 5
Song 6
```

Song 6 can be dragged directly to position 3:

```text
Song 1
Song 2
Song 6
Song 3
Song 4
Song 5
```

No up/down buttons are required.

---

# 💿 Playlists

LiteTube includes persistent playlists with a dedicated playlist interface.

### Playlist Navigation

The playlist system follows a simple two-level structure:

```text
Playlists
   ↓
Playlist List
   ↓
Select Playlist
   ↓
Playlist Details
   ↓
Songs
```

Opening the main **Playlists** section shows the playlist list first.

A playlist's songs are only displayed after selecting that specific playlist.

### Playlist Features

- Create playlists
- Persistent playlists
- Playlist data survives application restart
- Open individual playlists
- Play All
- Play individual songs
- Remove songs
- Drag-and-drop song reordering
- Dedicated playlist detail view
- Back navigation to playlist list

The original playlist order is preserved.

Playback can start from any selected song while continuing through the remaining playlist tracks in the correct order.

---

# 🕘 Playback History

LiteTube maintains recent playback history.

Features include:

- Recently played tracks
- Up to the latest 50 played songs
- Previous-track navigation
- History-aware playback
- Avoiding unnecessary duplicate history entries

History is stored locally.

---

# 🌍 Location-Based Music Discovery

LiteTube uses approximate public-IP-based location information to provide more relevant music discovery.

For example:

```text
User Location
      ↓
Approximate Country / Region
      ↓
Relevant Music Search
      ↓
Music Filter
      ↓
Artists + Songs
```

The location is used only to improve music discovery relevance.

LiteTube does not require users to manually enter their location.

---

# 🎨 Premium Glass Interface

LiteTube uses a modern glass-inspired interface designed for desktop music listening.

### Interface Features

- Glassmorphism design
- Transparent glass panels
- Light mode
- Dark mode
- Modern cards
- Rounded UI elements
- Smooth interactions
- Responsive layout
- Desktop-focused interface
- Music-focused visual hierarchy

The interface is intentionally lightweight while maintaining a premium appearance.

---

# 🖥️ Windows Desktop Application

LiteTube runs as a desktop application rather than requiring users to operate it through a normal browser tab.

The desktop application uses:

- Python
- Flask
- pywebview
- yt-dlp
- HTML
- CSS
- JavaScript

Architecture:

```text
Windows Desktop App
        │
        ▼
    pywebview
        │
        ▼
   Local Flask Server
        │
        ├── Music Search
        ├── Music Discovery
        ├── Playlists
        ├── Queue
        ├── History
        └── Audio Extraction
                │
                ▼
              yt-dlp
                │
                ▼
             YouTube
```

---

# 📦 Installation

## Requirements

LiteTube is designed for:

- Windows 10
- Windows 11
- Python 3.10 or newer
- Internet connection

---

## 🚀 Quick Start

### 1. Download LiteTube

Download or clone this repository.

### 2. Open the LiteTube folder

Make sure the following files are present:

```text
desktop.py
server.py
requirements.txt
run.bat
```

### 3. Run LiteTube

Double-click:

```text
run.bat
```

The application will start automatically.

---

# 🛠️ Manual Installation

If you want to install the project manually:

### Install dependencies

```bash
pip install -r requirements.txt
```

### Start LiteTube

```bash
python desktop.py
```

---

# 🏗️ Build the Windows Application

LiteTube includes a Windows build script.

Run:

```text
build_windows_desktop.bat
```

The script can be used to create the Windows desktop build.

---

# 📁 Project Structure

```text
LiteTube/
│
├── desktop.py
├── server.py
├── requirements.txt
├── LiteTube.ico
├── update_config.json
├── run.bat
├── build_windows_desktop.bat
├── README.md
├── VERSION.txt
│
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

---

# ⚙️ Configuration

LiteTube uses:

```text
update_config.json
```

for application update configuration.

The project also maintains local application data for user-specific information such as:

- Playlists
- Queue state
- Playback history
- Other local application state

User data is stored locally rather than requiring a remote database.

---

# 🔐 Privacy

LiteTube is designed as a lightweight local desktop application.

### LiteTube does not require:

- A YouTube Data API key
- A LiteTube account
- A remote database
- A mandatory YouTube login

### Local Data

User-specific application data such as playlists and playback history is stored locally.

### Location

Location-based discovery uses approximate public-IP-based location information to make music suggestions more relevant.

LiteTube does not require precise GPS location.

---

# 🌐 Network & Content

LiteTube uses YouTube as its music content source.

The application retrieves publicly available YouTube metadata and audio streams through its extraction layer.

LiteTube itself does not host or redistribute the underlying YouTube content.

---

# ⚠️ Disclaimer

LiteTube is an independent third-party project.

LiteTube is **not affiliated with, endorsed by, sponsored by, or officially connected to YouTube or Google.**

YouTube and related trademarks belong to their respective owners.

Content available through YouTube remains the property of its respective copyright holders.

Users are responsible for complying with:

- Applicable laws
- YouTube's Terms of Service
- Copyright requirements
- Rights of content owners

LiteTube should only be used in accordance with applicable laws and the terms governing the content being accessed.

---

# 🧩 Technology Stack

LiteTube is built using the following technologies:

| Technology | Purpose |
|---|---|
| Python | Application backend |
| Flask | Local web server |
| yt-dlp | YouTube extraction |
| pywebview | Windows desktop window |
| HTML | Application structure |
| CSS | Interface and visual design |
| JavaScript | Application logic |

---

# 📌 Current Version

## LiteTube v1.0.1

### v1.0.1 Highlights

- Location-based music discovery
- Artist suggestions
- Location-based song suggestions
- Music-focused search filtering
- Persistent playlists
- Dedicated playlist navigation
- Queue management
- Drag-and-drop queue ordering
- Playlist drag-and-drop ordering
- Playback history
- Audio-focused playback
- Light mode
- Dark mode
- More transparent glass interface
- Windows desktop application

---

# 🔄 Version History

## v1.0.1

Current stable release.

### Changes

- Added location-based artist discovery
- Added location-based song discovery
- Removed dependency on YouTube Home recommendations
- Removed Chrome cookie dependency for recommendations
- Improved music-focused discovery
- Improved playlist navigation
- Persistent playlist storage
- Updated transparent glass interface

---

# 🗺️ Roadmap

Possible future improvements may include:

- More advanced music discovery
- Improved artist pages
- Better recommendation personalization
- Additional playlist tools
- Improved library management
- More playback customization
- Performance improvements
- Additional Windows integrations

---

# ❤️ LiteTube

LiteTube is built around one simple idea:

> **Keep music listening simple.**

No unnecessary complexity.

Just search, discover, organize, and listen.

---

## 📄 License

This project is provided as an independent software project.

See the repository license for the applicable terms.
