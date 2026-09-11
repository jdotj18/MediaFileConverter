"""All formats and possible conversions."""

VIDEO_EXTS = {"mov", "avi", "mkv", "webm", "mp4"}
AUDIO_EXTS = {"mp3", "wav", "m4a", "aac", "flac"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"}

CONVERSIONS: dict[str, list[str]] = {
    # --- video ---
    "mov":  ["mp4", "mp3", "wav"],
    "avi":  ["mp4", "mp3", "wav"],
    "mkv":  ["mp4", "mp3", "wav"],
    "webm": ["mp4", "mp3", "wav"],
    "mp4":  ["mov", "webm", "mp3", "wav"],
    # --- audio ---
    "mp3":  ["wav", "m4a"],
    "wav":  ["mp3"],
    "m4a":  ["mp3"],
    "aac":  ["mp3"],
    "flac": ["mp3"],
    # --- images ---
    "jpg":  ["png", "webp"],
    "jpeg": ["png", "webp"],
    "png":  ["jpg", "webp"],
    "webp": ["png", "jpg"],
    "bmp":  ["png"],
    "tif":  ["png"],
    "tiff": ["png"],
}

SUPPORTED_EXTS = sorted(CONVERSIONS)

_LABELS = {"tif": "TIFF", "tiff": "TIFF", "jpg": "JPG", "jpeg": "JPEG"}


def kind_for_ext(ext: str) -> str:
    """Return 'video', 'audio', 'image' or 'unsupported'."""
    ext = ext.lower().lstrip(".")
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in IMAGE_EXTS:
        return "image"
    return "unsupported"


def outputs_for(ext: str) -> list[str]:
    """Compatible Conversions"""
    return list(CONVERSIONS.get(ext.lower().lstrip("."), []))


def job_kind(source_ext: str, target: str) -> str:
    #Settings
    target_kind = kind_for_ext(target)
    if target_kind in ("audio", "image"):
        return target_kind
    source_kind = kind_for_ext(source_ext)
    return "video" if source_kind == "unsupported" else source_kind


def label(ext: str) -> str:
    #Display Labels
    ext = ext.lower().lstrip(".")
    return _LABELS.get(ext, ext.upper())