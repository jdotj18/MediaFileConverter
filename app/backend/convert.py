"""Conversion worker and ffmpeg jobs"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .media import NO_WINDOW, MediaInfo, ffmpeg_path

H264_CRF = {"high": 18, "balanced": 23, "small": 28}
VP9_CRF = {"high": 28, "balanced": 33, "small": 38}
TARGET_HEIGHT = {"original": None, "1080p": 1080, "720p": 720, "480p": 480}

# ffmpeg -progress output all lowercase key=value lines
_PROGRESS_KEY = re.compile(r"^[a-z_0-9]+=")


@dataclass
class VideoSettings:
    resolution: str = "original"    # original, 1080p, 720p, 480p
    quality: str = "balanced"       # high, balanced, small
    fps: str = "original"           # original, 60, 30, 24
    preserve_audio: bool = True


@dataclass
class AudioSettings:
    bitrate: str = "192"            # 320, 256, 192, 128
    preserve_metadata: bool = True


@dataclass
class ImageSettings:
    quality: int = 85               # 1-100 (JPEG, WEBP)
    preserve_dimensions: bool = True
    width: int | None = None
    height: int | None = None
    maintain_aspect: bool = True


@dataclass
class Settings:
    video: VideoSettings = field(default_factory=VideoSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    image: ImageSettings = field(default_factory=ImageSettings)


def jpeg_quality(quality: int) -> int:
    """Sliders run 1-100; mjpeg's -q:v runs 2 (best) to 31 (worst)."""
    clamped = max(1, min(100, quality))
    return max(2, min(31, round(31 - (clamped / 100) * 29)))


def target_image_size(info: MediaInfo, settings: Settings) -> tuple[int, int] | None:
    """Final pixel size for an image job, or None if we can't tell."""
    if not info.width or not info.height:
        return None

    image = settings.image
    if image.preserve_dimensions or (not image.width and not image.height):
        return info.width, info.height

    want_w = image.width if image.width and image.width > 0 else None
    want_h = image.height if image.height and image.height > 0 else None

    if want_w and want_h:
        if not image.maintain_aspect:
            return want_w, want_h
        scale = min(want_w / info.width, want_h / info.height)
        return max(1, round(info.width * scale)), max(1, round(info.height * scale))
    if want_w:
        return want_w, max(1, round(info.height * want_w / info.width))
    if want_h:
        return max(1, round(info.width * want_h / info.height)), want_h
    return info.width, info.height


def _video_args(info: MediaInfo, target: str, s: Settings) -> list[str]:
    args = ["-i", str(info.path)]

    height = TARGET_HEIGHT[s.video.resolution]
    if height and info.height and info.height > height:
        args += ["-vf", f"scale=-2:{height}"]      # keep aspect ratio even

    if s.video.fps != "original":
        args += ["-r", s.video.fps]

    keep_audio = s.video.preserve_audio and info.has_audio

    if target == "webm":
        args += ["-c:v", "libvpx-vp9", "-crf", str(VP9_CRF[s.video.quality]),
                 "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "3"]
        args += ["-c:a", "libopus", "-b:a", f"{s.audio.bitrate}k"] if keep_audio else ["-an"]
    else:
        # mp4, mov get H.264, AAC
        args += ["-c:v", "libx264", "-preset", "medium",
                 "-crf", str(H264_CRF[s.video.quality]), "-pix_fmt", "yuv420p"]
        args += ["-c:a", "aac", "-b:a", f"{s.audio.bitrate}k"] if keep_audio else ["-an"]
        args += ["-movflags", "+faststart"]

    return args


def _audio_args(info: MediaInfo, target: str, s: Settings) -> list[str]:
    args = ["-i", str(info.path), "-vn"]
    args += ["-map_metadata", "0" if s.audio.preserve_metadata else "-1"]

    if target == "mp3":
        args += ["-c:a", "libmp3lame", "-b:a", f"{s.audio.bitrate}k", "-id3v2_version", "3"]
    elif target == "wav":
        args += ["-c:a", "pcm_s16le"]
    else:  # m4a
        args += ["-c:a", "aac", "-b:a", f"{s.audio.bitrate}k", "-movflags", "+faststart"]

    return args


def _image_args(info: MediaInfo, target: str, s: Settings) -> list[str]:
    size = target_image_size(info, s)
    args = ["-i", str(info.path)]

    if target in ("jpg", "jpeg") and info.has_alpha and size:
        # place white background behind png
        width, height = size
        args += [
            "-f", "lavfi", "-i", f"color=white:s={width}x{height}",
            "-filter_complex",
            f"[0:v]scale={width}:{height},format=rgba[fg];"
            f"[1:v][fg]overlay=format=auto,format=yuv420p[out]",
            "-map", "[out]",
        ]
    elif size and (size[0] != info.width or size[1] != info.height):
        args += ["-vf", f"scale={size[0]}:{size[1]}"]

    if target in ("jpg", "jpeg"):
        args += ["-q:v", str(jpeg_quality(s.image.quality))]
    elif target == "webp":
        args += ["-c:v", "libwebp", "-quality", str(max(1, min(100, s.image.quality)))]
    else:  # png
        args += ["-compression_level", "6"]

    args += ["-frames:v", "1", "-update", "1"]
    return args


def build_args(info: MediaInfo, target: str, output: Path, settings: Settings) -> list[str]:

    target = target.lower()
    #-progress writes key=value lines to stdout
    args = [ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error",
            "-progress", "pipe:1", "-nostats"]

    if info.kind == "image" and target in ("png", "jpg", "jpeg", "webp"):
        args += _image_args(info, target, settings)
    elif target in ("mp3", "wav", "m4a"):
        args += _audio_args(info, target, settings)
    else:
        args += _video_args(info, target, settings)

    args.append(str(output))
    return args


def unique_output_path(source: Path, target: str, output_dir: Path | None) -> Path:
    #photo.png -> photo.jpg -> photo (1).jpg
    folder = Path(output_dir) if output_dir else source.parent
    folder.mkdir(parents=True, exist_ok=True)
    ext = "jpg" if target == "jpeg" else target

    candidate = folder / f"{source.stem}.{ext}"
    if candidate.resolve() == source.resolve():
        candidate = folder / f"{source.stem} (converted).{ext}"

    counter = 1
    while candidate.exists():
        candidate = folder / f"{source.stem} ({counter}).{ext}"
        counter += 1
    return candidate


class ConversionWorker(QThread):
    """Runs queue one by one on background thread. One at a time keeps conversiom progress honest and makes cancelling easier."""

    job_started = Signal(int)
    job_progress = Signal(int, int)     # row id, percent
    job_done = Signal(int, str)         # row id, output path
    job_failed = Signal(int, str)       # row id, message
    all_finished = Signal()

    def __init__(self, jobs, settings: Settings, output_dir, parent=None):
        super().__init__(parent)
        self._jobs = jobs               # list of (row_id, MediaInfo, target)
        self._settings = settings
        self._output_dir = output_dir
        self._process = None
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        process = self._process
        if process and process.poll() is None:
            process.kill()

    def run(self) -> None:
        for row_id, info, target in self._jobs:
            if self._cancelled:
                break
            self.job_started.emit(row_id)
            try:
                self._run_one(row_id, info, target)
            except Exception as exc:
                self.job_failed.emit(row_id, str(exc))
        self.all_finished.emit()

    def _run_one(self, row_id: int, info: MediaInfo, target: str) -> None:
        output = unique_output_path(info.path, target, self._output_dir)
        args = build_args(info, target, output, self._settings)

        self._process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW,
        )

        messages: list[str] = []
        highest = 0

        if not info.duration:
            self.job_progress.emit(row_id, 25)

        for raw in self._process.stdout:
            line = raw.strip()
            if not line:
                continue
            if not _PROGRESS_KEY.match(line):
                messages.append(line)
                del messages[:-5]
                continue
            key, _, value = line.partition("=")
            if key == "out_time_us" and info.duration and value.isdigit():
                percent = min(99, int(int(value) / 1_000_000 / info.duration * 100))
                if percent > highest:
                    highest = percent
                    self.job_progress.emit(row_id, percent)

        code = self._process.wait()
        self._process = None

        if self._cancelled:
            output.unlink(missing_ok=True)
            return

        if code != 0:
            output.unlink(missing_ok=True)
            reason = messages[-1] if messages else f"ffmpeg exited with code {code}"
            self.job_failed.emit(row_id, reason)
            return

        self.job_progress.emit(row_id, 100)
        self.job_done.emit(row_id, str(output))