from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import OrderedDict
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
import yt_dlp
from flask import Flask, jsonify, request, send_from_directory

APP_HOST = "127.0.0.1"
APP_PORT = 8000
APP_VERSION = "1.0.0"

SEARCH_CACHE_TTL = 60
SUGGEST_CACHE_TTL = 15
META_CACHE_TTL = 180
AUDIO_CACHE_TTL = 45
RECOMMEND_CACHE_TTL = 300
MAX_CACHE_ITEMS = 120

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


def search_youtube(query: str, limit: int = 30) -> list[dict[str, Any]]:
    cache_key = f"{query.casefold().strip()}:{limit}"
    cached = cache_get("search", cache_key)
    if cached is not None:
        return cached

    info = extract_info(f"ytsearch{limit}:{query}", extract_flat=True)
    results: list[dict[str, Any]] = []

    for entry in info.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        track = normalize_entry(entry)
        if track:
            results.append(track)

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


def get_recommendations() -> list[dict[str, Any]]:
    cached = cache_get("recommend", "home")
    if cached is not None:
        return cached

    # Real YouTube searches, not hardcoded song data.
    discovery_queries = [
        "popular songs 2026",
        "new music 2026",
        "viral songs 2026",
        "best chill songs",
    ]

    combined: list[dict[str, Any]] = []
    seen: set[str] = set()

    for query in discovery_queries:
        try:
            for track in search_youtube(query, limit=8):
                if track["id"] not in seen:
                    seen.add(track["id"])
                    combined.append(track)
                if len(combined) >= 20:
                    break
        except LiteTubeError as exc:
            logger.warning("Recommendation query failed: %s", exc)

        if len(combined) >= 20:
            break

    cache_put("recommend", "home", combined, RECOMMEND_CACHE_TTL)
    return combined


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


@app.get("/api/playlist")
def api_playlist() -> Any:
    try:
        return jsonify(load_playlist(request.args.get("url", "").strip()))
    except LiteTubeError as exc:
        return jsonify({"title": "", "tracks": [], "error": str(exc)}), 422


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
