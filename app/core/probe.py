import json
import math
import subprocess
import sys
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
    bitrate: Optional[int] = None  # 视频码率，单位 bps (例如 11000000 即 11 Mbps)

    @property
    def bitrate_mbps(self) -> Optional[float]:
        if self.bitrate and self.bitrate > 0:
            return round(self.bitrate / 1_000_000, 2)
        return None

    @property
    def bitrate_str(self) -> str:
        if self.bitrate and self.bitrate > 0:
            mbps = self.bitrate / 1_000_000
            if mbps >= 1.0:
                return f"{mbps:.1f} Mbps"
            else:
                return f"{round(self.bitrate / 1000)} kbps"
        return "未知"


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
            "stream=width,height,duration,codec_type,bit_rate:stream_disposition=attached_pic",
            "-show_entries",
            "format=duration,bit_rate,size",
            "-of",
            "json",
            str(p),
        ]

        run_kwargs = {
            "capture_output": True,
            "encoding": "utf-8",
            "errors": "replace",
            "check": True,
            "timeout": 10.0,
        }
        if sys.platform == "win32":
            run_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        try:
            res = subprocess.run(cmd, **run_kwargs)
            data = json.loads(res.stdout)
        except Exception:
            return None

        streams = data.get("streams", [])
        video_stream = None
        has_audio = False

        for s in streams:
            codec_type = s.get("codec_type")
            disposition = s.get("disposition") or {}
            is_attached_pic = bool(disposition.get("attached_pic"))

            if codec_type == "video" and not is_attached_pic and video_stream is None:
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

        if not math.isfinite(duration) or duration < 0:
            duration = 0.0

        ext = p.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            is_video = True
        elif ext in IMAGE_EXTENSIONS:
            is_video = False
        else:
            is_video = duration > 0.0

        # 视频码率探测 (bps)
        bitrate: Optional[int] = None
        if is_video:
            # 1. 优先从视频流属性提取
            raw_br = video_stream.get("bit_rate")
            if raw_br:
                try:
                    b = int(raw_br)
                    if b > 0:
                        bitrate = b
                except (ValueError, TypeError):
                    pass

            # 2. 从封装容器 format 读取并适当扣除音频开销
            if bitrate is None:
                raw_fmt_br = format_info.get("bit_rate")
                if raw_fmt_br:
                    try:
                        b = int(raw_fmt_br)
                        if b > 0:
                            audio_est = 128_000 if has_audio else 0
                            bitrate = max(100_000, b - audio_est)
                    except (ValueError, TypeError):
                        pass

            # 3. 兜底根据文件物理大小和时长估算
            if bitrate is None and duration > 0.1:
                try:
                    file_size = p.stat().st_size
                    b = int((file_size * 8) / duration)
                    if b > 0:
                        audio_est = 128_000 if has_audio else 0
                        bitrate = max(100_000, b - audio_est)
                except Exception:
                    pass

        return MediaInfo(
            width=width,
            height=height,
            duration=duration,
            is_video=is_video,
            has_audio=has_audio,
            bitrate=bitrate,
        )
