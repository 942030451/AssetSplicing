import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".m4v", ".wmv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


@dataclass
class MediaInfo:
    width: int
    height: int
    duration: float
    is_video: bool
    has_audio: bool


class MediaProbe:
    def __init__(self, ffprobe_bin: Union[str, Path] = "ffprobe"):
        self.ffprobe_bin = str(ffprobe_bin)

    def probe(self, file_path: Union[str, Path]) -> Optional[MediaInfo]:
        try:
            p = Path(file_path)
            if not p.is_file():
                return None
        except Exception:
            return None

        cmd = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "stream=width,height,duration,codec_type",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(p),
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
        except Exception:
            return None

        streams = data.get("streams", [])
        video_stream = None
        has_audio = False

        for s in streams:
            codec_type = s.get("codec_type")
            if codec_type == "video" and video_stream is None:
                video_stream = s
            elif codec_type == "audio":
                has_audio = True

        if not video_stream:
            return None

        try:
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
        except (ValueError, TypeError):
            return None

        if width <= 0 or height <= 0:
            return None

        format_info = data.get("format", {})
        duration_str = format_info.get("duration") or video_stream.get("duration") or "0"
        try:
            duration = float(duration_str)
        except (ValueError, TypeError):
            duration = 0.0

        if duration < 0:
            duration = 0.0

        ext = p.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            is_video = True
        elif ext in IMAGE_EXTENSIONS:
            is_video = False
        else:
            is_video = duration > 0.0

        return MediaInfo(
            width=width,
            height=height,
            duration=duration,
            is_video=is_video,
            has_audio=has_audio,
        )
