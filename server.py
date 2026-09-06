from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from collections import OrderedDict
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
import yt_dlp
from flask import Flask, jsonify, request, send_from_directory

APP_HOST = "127.0.0.1"
APP_PORT = 8000
APP_VERSION = "1.0.1"

SEARCH_CACHE_TTL = 60
SUGGEST_CACHE_TTL = 15
META_CACHE_TTL = 180
AUDIO_CACHE_TTL = 45
ARTIST_CACHE_TTL = 1800
MAX_CACHE_ITEMS = 120

APP_DATA_DIR = Path(os.environ.get("APPDATA") or (Path.home() / ".config")) / "LiteTube"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = APP_DATA_DIR / "data.json"
_STATE_LOCK = threading.RLock()

NON_MUSIC_PATTERNS = (
    "playlist", "nonstop", "non-stop", "compilation", "jukebox", "mega mix",
    "megamiх", "mix of", "best of", "top 10", "top 20", "top 50", "top 100",
    "greatest hits", "radio", "podcast", "reaction", "reacts to", "interview",
    "news", "review", "explained", "tutorial", "how to", "documentary",
    "gameplay", "walkthrough", "vlog", "live stream", "livestream",
)

QUALITY_TARGETS = {48: 48, 64: 64, 96: 96, 128: 128}

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}

app = Flask(__name__, static_folder="static", static_url_path="/static")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("litetube")

_cache_lock = threading.RLock()
_caches: dict[str, OrderedDict[str, tuple[float, Any]]] = {
    "search": OrderedDict(),
    "suggest": OrderedDict(),
    "meta": OrderedDict(),
    "audio": OrderedDict(),
    "recommend": OrderedDict(),
    "artist": OrderedDict(),
}


class LiteTubeError(Exception):
    pass


def cache_get(bucket: str, key: str) -> Any | None:
    now = time.time()
    with _cache_lock:
        item = _caches[bucket].get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= now:
            _caches[bucket].pop(key, None)
            return None
        _caches[bucket].move_to_end(key)
        return value


def cache_put(bucket: str, key: str, value: Any, ttl: int) -> None:
    with _cache_lock:
        cache = _caches[bucket]
        cache[key] = (time.time() + ttl, value)
        cache.move_to_end(key)
        while len(cache) > MAX_CACHE_ITEMS:
            cache.popitem(last=False)


def youtube_video_id(value: str) -> str | None:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None

    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        return None

    path = parsed.path.strip("/")

    if host == "youtu.be":
        candidate = path.split("/")[0] if path else ""
        return candidate if re.fullmatch(r"[\w-]{11}", candidate) else None

    if path == "watch":
        candidate = parse_qs(parsed.query).get("v", [""])[0]
        return candidate if re.fullmatch(r"[\w-]{11}", candidate) else None

    for prefix in ("shorts/", "embed/", "live/"):
        if path.startswith(prefix):
            candidate = path[len(prefix):].split("/")[0]
            return candidate if re.fullmatch(r"[\w-]{11}", candidate) else None

    return None


def youtube_playlist_id(value: str) -> str | None:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None

    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        return None

    playlist_id = parse_qs(parsed.query).get("list", [""])[0]
    return playlist_id or None


def is_mix_playlist_id(playlist_id: str) -> bool:
    return playlist_id.upper().startswith("RD")


def normalize_duration(value: Any) -> int | None:
    try:
        seconds = int(float(value))
        return seconds if seconds >= 0 else None
    except (TypeError, ValueError):
        return None


def thumbnail_for(video_id: str, provided: str | None = None) -> str:
    return provided or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def normalize_video(info: dict[str, Any]) -> dict[str, Any] | None:
    video_id = str(info.get("id") or "").strip()
    if not re.fullmatch(r"[\w-]{11}", video_id):
        return None

    return {
        "id": video_id,
        "title": str(info.get("title") or "Untitled").strip(),
        "artist": str(
            info.get("artist")
            or info.get("uploader")
            or info.get("channel")
            or "YouTube"
        ).strip(),
        "thumbnail": thumbnail_for(video_id, info.get("thumbnail")),
        "duration": normalize_duration(info.get("duration")),
        "url": str(
            info.get("webpage_url")
            or f"https://www.youtube.com/watch?v={video_id}"
        ),
    }


def normalize_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    video_id = str(entry.get("id") or "").strip()
    if not re.fullmatch(r"[\w-]{11}", video_id):
        return None

    return {
        "id": video_id,
        "title": str(entry.get("title") or "Untitled").strip(),
        "artist": str(
            entry.get("artist")
            or entry.get("uploader")
            or entry.get("channel")
            or entry.get("creator")
            or "YouTube"
        ).strip(),
        "thumbnail": thumbnail_for(video_id, entry.get("thumbnail")),
        "duration": normalize_duration(entry.get("duration")),
        "url": str(
            entry.get("webpage_url")
            or f"https://www.youtube.com/watch?v={video_id}"
        ),
    }


def ydl_options(**overrides: Any) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "cachedir": False,
        "socket_timeout": 15,
        "retries": 2,
        "fragment_retries": 2,
        "extractor_retries": 2,
        "concurrent_fragment_downloads": 1,
    }
    options.update(overrides)
    return options


def extract_info(url: str, **overrides: Any) -> dict[str, Any]:
    try:
        with yt_dlp.YoutubeDL(ydl_options(**overrides)) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as exc:
        logger.exception("yt-dlp extraction failed for %s", url)
        raise LiteTubeError(f"yt-dlp could not process this request: {exc}") from exc


def is_music_track(track: dict[str, Any]) -> bool:
    """Shared music-only filter used by Home recommendations and Search."""
    title = str(track.get("title") or "").casefold()
    artist = str(track.get("artist") or "").casefold()
    text = f"{title} {artist}"

    if any(pattern in text for pattern in NON_MUSIC_PATTERNS):
        return False

    duration = track.get("duration")
    if duration is not None:
        try:
            seconds = int(duration)
        except (TypeError, ValueError):
            seconds = 0
        # Very long videos are overwhelmingly mixes, podcasts, shows or compilations.
        if seconds > 900:
            return False

    return True


def filter_music_tracks(tracks: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for track in tracks:
        if not is_music_track(track) or track["id"] in seen:
            continue
        seen.add(track["id"])
        results.append(track)
        if len(results) >= limit:
            break
    return results


def search_youtube(query: str, limit: int = 30) -> list[dict[str, Any]]:
    cache_key = f"{query.casefold().strip()}:{limit}"
    cached = cache_get("search", cache_key)
    if cached is not None:
        return cached

    # Fetch a larger pool because the shared music filter removes non-music videos.
    info = extract_info(f"ytsearch{max(limit * 2, 60)}:{query}", extract_flat=True)
    candidates: list[dict[str, Any]] = []

    for entry in info.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        track = normalize_entry(entry)
        if track:
            candidates.append(track)

    results = filter_music_tracks(candidates, limit)
    cache_put("search", cache_key, results, SEARCH_CACHE_TTL)
    return results


def load_playlist(url: str) -> dict[str, Any]:
    playlist_id = youtube_playlist_id(url)
    if not playlist_id:
        raise LiteTubeError("Please enter a valid YouTube playlist URL.")

    if is_mix_playlist_id(playlist_id):
        raise LiteTubeError(
            "This is a YouTube Mix/radio URL. Please use a normal YouTube playlist URL."
        )

    cache_key = f"playlist:{playlist_id}"
    cached = cache_get("meta", cache_key)
    if cached is not None:
        return cached

    try:
        with yt_dlp.YoutubeDL(
            ydl_options(extract_flat="in_playlist", noplaylist=False)
        ) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        logger.exception("Playlist extraction failed for %s", url)
        raise LiteTubeError(f"Playlist could not be loaded: {exc}") from exc

    tracks = []
    for entry in info.get("entries") or []:
        if isinstance(entry, dict):
            track = normalize_entry(entry)
            if track:
                tracks.append(track)

    if not tracks:
        raise LiteTubeError("No accessible songs were found in this playlist.")

    result = {
        "title": str(info.get("title") or "YouTube Playlist"),
        "tracks": tracks,
    }
    cache_put("meta", cache_key, result, META_CACHE_TTL)
    return result


def choose_audio_format(info: dict[str, Any], requested_kbps: int) -> dict[str, Any]:
    formats = info.get("formats") or []
    audio_formats: list[dict[str, Any]] = []

    for fmt in formats:
        if not isinstance(fmt, dict) or not fmt.get("url"):
            continue
        if fmt.get("vcodec") not in (None, "none"):
            continue

        try:
            bitrate = float(fmt.get("abr"))
        except (TypeError, ValueError):
            bitrate = 99999.0

        copy = dict(fmt)
        copy["_bitrate"] = bitrate
        audio_formats.append(copy)

    if not audio_formats:
        raise LiteTubeError("No audio-only stream is available for this video.")

    target = float(requested_kbps)
    below = [f for f in audio_formats if f["_bitrate"] <= target]

    if below:
        below.sort(
            key=lambda f: (
                abs(f["_bitrate"] - target),
                0 if f.get("ext") == "m4a" else 1,
                -f["_bitrate"],
            )
        )
        return below[0]

    audio_formats.sort(
        key=lambda f: (
            f["_bitrate"],
            0 if f.get("ext") == "m4a" else 1,
        )
    )
    return audio_formats[0]


def get_audio(video_id: str, requested_kbps: int) -> dict[str, Any]:
    if requested_kbps not in QUALITY_TARGETS:
        raise LiteTubeError("Choose 48k, 64k, 96k, or 128k.")

    cache_key = f"{video_id}:{requested_kbps}"
    cached = cache_get("audio", cache_key)
    if cached is not None:
        return cached

    info = extract_info(f"https://www.youtube.com/watch?v={video_id}")
    normalized = normalize_video(info)
    if not normalized:
        raise LiteTubeError("Unable to read this song's metadata.")

    fmt = choose_audio_format(info, requested_kbps)
    actual_quality = (
        round(fmt["_bitrate"]) if fmt["_bitrate"] < 99999 else None
    )

    result = {
        "url": fmt["url"],
        "title": normalized["title"],
        "artist": normalized["artist"],
        "duration": normalized["duration"],
        "thumbnail": normalized["thumbnail"],
        "quality": actual_quality,
        "requested_quality": requested_kbps,
        "ext": fmt.get("ext"),
    }
    cache_put("audio", cache_key, result, AUDIO_CACHE_TTL)
    return result


def parse_suggestions_payload(response: requests.Response) -> list[str]:
    text = response.text.strip()
    if not text:
        return []

    try:
        data = response.json()
    except ValueError:
        match = re.search(r"\(\s*(\{.*\}|\[.*\])\s*\)\s*;?\s*$", text, re.S)
        if not match:
            return []
        try:
            import json
            data = json.loads(match.group(1))
        except ValueError:
            return []

    suggestions: list[str] = []

    def add(value: Any) -> None:
        if not isinstance(value, str):
            return
        value = value.strip()
        if value and value.casefold() not in {x.casefold() for x in suggestions}:
            suggestions.append(value)

    if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
        for item in data[1]:
            if isinstance(item, str):
                add(item)
            elif isinstance(item, dict):
                add(item.get("suggestion") or item.get("query") or item.get("text"))
    elif isinstance(data, list):
        for item in data:
            add(item)
    elif isinstance(data, dict):
        for key in ("suggestion", "query", "text", "title"):
            add(data.get(key))

    return suggestions[:8]


def get_suggestions(query: str) -> list[str]:
    cache_key = query.casefold().strip()
    cached = cache_get("suggest", cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(
            "https://suggestqueries.google.com/complete/search",
            params={"client": "firefox", "q": query},
            timeout=4,
            headers={
                "User-Agent": "Mozilla/5.0 LiteTube/1.0",
                "Accept": "application/json,text/javascript,*/*;q=0.8",
            },
        )
        response.raise_for_status()
        suggestions = parse_suggestions_payload(response)
    except Exception as exc:
        logger.warning("Suggestion request failed: %s", exc)
        suggestions = []

    cache_put("suggest", cache_key, suggestions, SUGGEST_CACHE_TTL)
    return suggestions


def get_public_location() -> dict[str, str]:
    """Resolve the machine's public IP location for localized music discovery."""
    cached = cache_get("artist", "location")
    if cached is not None:
        return cached
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5, headers={"User-Agent": "LiteTube/1.0"})
        response.raise_for_status()
        data = response.json()
        result = {
            "ip": str(data.get("ip") or ""),
            "city": str(data.get("city") or ""),
            "region": str(data.get("region") or ""),
            "country": str(data.get("country_name") or ""),
            "country_code": str(data.get("country_code") or "").upper(),
        }
    except Exception as exc:
        logger.warning("IP geolocation failed: %s", exc)
        result = {"ip": "", "city": "", "region": "", "country": "", "country_code": ""}
    cache_put("artist", "location", result, ARTIST_CACHE_TTL)
    return result


def get_local_artists() -> dict[str, Any]:
    location = get_public_location()
    country = location.get("country") or "global"
    code = location.get("country_code") or ""
    cache_key = f"artists:{code or country.casefold()}"
    cached = cache_get("artist", cache_key)
    if cached is not None:
        return cached

    if code == "IN" or country.casefold() == "india":
        queries = [
            "popular Indian songs 2026",
            "new Indian songs 2026",
            "Indian music artists 2026",
        ]
    else:
        queries = [
            f"popular {country} songs 2026",
            f"new {country} songs 2026",
            f"popular {country} music artists 2026",
        ] if country != "global" else ["popular songs 2026", "new music 2026", "popular music artists 2026"]

    candidates: list[dict[str, Any]] = []
    for query in queries:
        try:
            candidates.extend(search_youtube(query, limit=15))
        except LiteTubeError as exc:
            logger.warning("Localized artist query failed for %s: %s", query, exc)

    songs = filter_music_tracks(candidates, 18)
    artists: list[dict[str, Any]] = []
    seen: set[str] = set()
    for track in songs:
        artist = str(track.get("artist") or "").strip()
        if not artist or artist.casefold() in seen:
            continue
        seen.add(artist.casefold())
        artists.append({"name": artist, "track": track})
        if len(artists) >= 12:
            break

    result = {"location": location, "artists": artists, "songs": songs}
    cache_put("artist", cache_key, result, ARTIST_CACHE_TTL)
    return result


def get_recommendations() -> list[dict[str, Any]]:
    cached = cache_get("recommend", "home")
    if cached is not None:
        return cached

    # Use YouTube's actual Home / Recommended feed. No search queries are used.
    # yt-dlp exposes this feed through the youtube:recommended extractor.
    try:
        info = extract_info(
            "https://www.youtube.com/",
            extract_flat=True,
            noplaylist=False,
            playlistend=60,
            lazy_playlist=True,
        )
    except LiteTubeError as exc:
        logger.warning("YouTube Home feed failed: %s", exc)
        return []

    candidates: list[dict[str, Any]] = []
    for entry in info.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        track = normalize_entry(entry)
        if track:
            candidates.append(track)

    results = filter_music_tracks(candidates, 20)
    cache_put("recommend", "home", results, RECOMMEND_CACHE_TTL)
    return results


def load_app_state() -> dict[str, Any]:
    with _STATE_LOCK:
        try:
            if not STATE_FILE.exists():
                return {"playlists": []}
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"playlists": []}
        except Exception as exc:
            logger.warning("Could not read app state: %s", exc)
            return {"playlists": []}


def save_app_state(data: dict[str, Any]) -> None:
    with _STATE_LOCK:
        temp_file = STATE_FILE.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_file.replace(STATE_FILE)


@app.get("/")
def index() -> Any:
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/version")
def api_version() -> Any:
    return jsonify({"version": APP_VERSION})

@app.get("/update_config.json")
def update_config() -> Any:
    return send_from_directory(app.root_path, "update_config.json", mimetype="application/json")



@app.get("/api/health")
def health() -> Any:
    return jsonify({"status": "ok", "service": "LiteTube"})


@app.get("/api/search")
def api_search() -> Any:
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"results": [], "message": "Enter something to search."})

    video_id = youtube_video_id(query)
    if video_id:
        try:
            info = extract_info(f"https://www.youtube.com/watch?v={video_id}")
            result = normalize_video(info)
            if not result:
                raise LiteTubeError("Unable to read that YouTube video.")
            return jsonify({"results": [result], "source": "video"})
        except LiteTubeError as exc:
            return jsonify({"results": [], "error": str(exc)}), 422

    if youtube_playlist_id(query):
        return jsonify(
            {
                "results": [],
                "playlist_url": query,
                "error": "This is a playlist URL. Use the playlist loader.",
            }
        ), 400

    try:
        return jsonify(
            {"results": search_youtube(query, limit=30), "source": "search"}
        )
    except LiteTubeError as exc:
        return jsonify({"results": [], "error": str(exc)}), 502


@app.get("/api/suggest")
def api_suggest() -> Any:
    query = request.args.get("q", "").strip()
    return jsonify(
        {"suggestions": get_suggestions(query) if len(query) >= 2 else []}
    )


@app.get("/api/state")
def api_state_get() -> Any:
    return jsonify(load_app_state())


@app.put("/api/state")
def api_state_put() -> Any:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid state payload."}), 400

    playlists = payload.get("playlists", [])
    if not isinstance(playlists, list):
        return jsonify({"error": "Invalid playlists payload."}), 400

    save_app_state({"playlists": playlists})
    return jsonify({"ok": True})


@app.get("/api/playlist")
def api_playlist() -> Any:
    try:
        return jsonify(load_playlist(request.args.get("url", "").strip()))
    except LiteTubeError as exc:
        return jsonify({"title": "", "tracks": [], "error": str(exc)}), 422


@app.get("/api/artists")
def api_artists() -> Any:
    try:
        return jsonify(get_local_artists())
    except Exception:
        logger.exception("Artist discovery endpoint failed")
        return jsonify({"location": {}, "artists": [], "songs": [], "error": "Artist discovery is temporarily unavailable."}), 200


@app.get("/api/recommendations")
def api_recommendations() -> Any:
    try:
        return jsonify({"results": get_recommendations()})
    except Exception:
        logger.exception("Recommendation endpoint failed")
        return jsonify(
            {
                "results": [],
                "error": "Recommendations are temporarily unavailable.",
            }
        ), 200


@app.get("/api/audio/<video_id>")
def api_audio(video_id: str) -> Any:
    if not re.fullmatch(r"[\w-]{11}", video_id):
        return jsonify({"error": "Invalid YouTube video ID."}), 400

    try:
        quality = int(request.args.get("quality", "64"))
    except ValueError:
        quality = 64

    try:
        return jsonify(get_audio(video_id, quality))
    except LiteTubeError as exc:
        return jsonify({"error": str(exc)}), 422


@app.errorhandler(404)
def not_found(error: Any) -> Any:
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found."}), 404
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(Exception)
def unhandled(error: Exception) -> Any:
    logger.exception("Unhandled server error")
    if request.path.startswith("/api/"):
        return jsonify({"error": "An unexpected server error occurred."}), 500
    return "Internal server error", 500


def run_server() -> None:
    logger.info("LiteTube running at http://%s:%s", APP_HOST, APP_PORT)
    app.run(host=APP_HOST, port=APP_PORT, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    # Source-mode fallback: run the local Flask server directly.
    # The Windows desktop build uses desktop.py + pywebview instead.
    run_server()
