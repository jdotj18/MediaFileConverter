"""Reading media file."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import imageio_ffmpeg

from .formats import kind_for_ext, outputs_for

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)")
_SIZE_RE = re.compile(r"(?<!\d)(\d{2,5})x(\d{2,5})(?!\d)")
_FPS_RE = re.compile(r"(\d+(?:\.\d+)?)\s+fps")
_ALPHA_RE = re.compile(r"\b(rgba|bgra|argb|abgr|ya8|ya16|yuva\w*|pal8|rgba64\w*)\b")


def ffmpeg_path() -> str:
    #Absolute path to the ffmpeg binary that came with imageio-ffmpeg.
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_hidden(args: list[str]) -> subprocess.CompletedProcess:

    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=NO_WINDOW,
    )


@dataclass
class MediaInfo:
    path: Path
    name: str
    ext: str
    size: int = 0
    kind: str = "unsupported"
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    has_audio: bool = False
    has_alpha: bool = False
    outputs: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def supported(self) -> bool:
        return bool(self.outputs) and self.error is None


def probe(file_path: str | Path) -> MediaInfo:
    #Read files's true properties
    path = Path(file_path)
    ext = path.suffix.lstrip(".").lower()
    info = MediaInfo(
        path=path,
        name=path.name,
        ext=ext,
        kind=kind_for_ext(ext),
        outputs=outputs_for(ext),
    )

    if not path.is_file():
        info.error = "File could not be read"
        info.outputs = []
        return info

    info.size = path.stat().st_size

    if not info.outputs:
        info.error = f"{ext.upper() or 'This file type'} is not supported"
        return info

    #no output file makes ffmpeg describe input then exit non-zero
    try:
        result = run_hidden([ffmpeg_path(), "-hide_banner", "-i", str(path)])
    except Exception:
        info.error = "ffmpeg is not available"
        return info

    text = result.stderr

    if "Invalid data found" in text or "No such file" in text:
        info.error = "This file is damaged or not a real media file"
        return info

    duration = _DURATION_RE.search(text)
    if duration and info.kind != "image":
        hours, minutes, seconds = duration.groups()
        total = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        info.duration = total if total > 0 else None

    for line in text.splitlines():
        if ": Audio:" in line:
            info.has_audio = True
        elif ": Video:" in line and info.width is None:
            size = _SIZE_RE.search(line)
            if size:
                info.width, info.height = int(size.group(1)), int(size.group(2))
            fps = _FPS_RE.search(line)
            if fps:
                info.fps = float(fps.group(1))
            info.has_alpha = bool(_ALPHA_RE.search(line))

    return info


def format_bytes(count: int) -> str:
    """1536 -> '1.5 KB'"""
    if count <= 0:
        return "-"
    size = float(count)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if size >= 10 or unit == "B":
                return f"{size:.0f} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_duration(seconds: float | None) -> str:
    """125 -> '2:05'"""
    if not seconds or seconds <= 0:
        return "-"
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"