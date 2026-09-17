"""calling yt-dlp"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

from yt_dlp import YoutubeDL

from .media import ffmpeg_path

YOUTUBE_URL = re.compile(
    r"^(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|shorts/|live/|embed/)[\w-]{6,}"
    r"|youtu\.be/[\w-]{6,})",
    re.IGNORECASE,
)


class Cancelled(Exception):
    """stop download"""


def is_valid_url(url: str) -> bool:
    return bool(YOUTUBE_URL.match(url.strip()))


def ffmpeg_dir() -> str:
    #yt-dlp wants ffmpeg.exe, imageio ships versioned name
    source = Path(ffmpeg_path())
    folder = Path(tempfile.gettempdir()) / "converter-ffmpeg"
    folder.mkdir(exist_ok=True)
    target = folder / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")

    if not target.exists():
        try:
            os.link(source, target)      # instant, no extra disk space
        except OSError:
            shutil.copy2(source, target)  # different volume - copy instead
    return str(folder)


def fetch_info(url: str) -> dict:
    """Check for valid link"""
    if not is_valid_url(url):
        raise ValueError("That does not look like a YouTube video link.")

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    with YoutubeDL(options) as ydl:
        raw = ydl.extract_info(url.strip(), download=False)

    if raw.get("_type") == "playlist":
        raise ValueError("Playlists are not supported. Paste a single video link.")

    heights = sorted(
        {
            fmt["height"]
            for fmt in raw.get("formats", [])
            if fmt.get("vcodec") not in (None, "none") and fmt.get("height")
        },
        reverse=True,
    )

    return {
        "title": raw.get("title") or "Untitled",
        "channel": raw.get("channel") or raw.get("uploader") or "Unknown channel",
        "duration": raw.get("duration") or 0,
        "thumbnail": raw.get("thumbnail"),
        "heights": heights,
        "url": raw.get("webpage_url") or url.strip(),
    }


def fetch_thumbnail(url: str | None) -> bytes | None:
    #urlopen follows file:// too
    if not url or not url.startswith(("http://", "https://")):
        return None
    try:
        with urlopen(url, timeout=10) as response:
            return response.read()
    except Exception:
        return None


def build_options(mode, height, bitrate, output_dir, progress_hooks, post_hooks) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "windowsfilenames": True,
        "outtmpl": str(Path(output_dir) / "%(title).120B.%(ext)s"),
        "ffmpeg_location": ffmpeg_dir(),
        "progress_hooks": progress_hooks,
        "postprocessor_hooks": post_hooks,
    }

    if mode == "mp3":
        options["format"] = "ba/b"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(bitrate),
            },
            {"key": "FFmpegMetadata"},
        ]
    else:
        cap = f"[height<={height}]" if height else ""
        options["format"] = (
            f"bv*{cap}[ext=mp4]+ba[ext=m4a]/bv*{cap}+ba/b{cap}/b"
        )
        options["merge_output_format"] = "mp4"
        options["postprocessors"] = [{"key": "FFmpegMetadata"}]

    return options


def download(options: dict, url: str) -> str | None:
    """Run download, return file destination"""
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    finished = info.get("requested_downloads") or []
    return finished[0].get("filepath") if finished else None