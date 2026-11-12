from pathlib import Path
from typing import List, Optional, Union


class PipelineBuilder:
    @staticmethod
    def calculate_part_width(w: int, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be greater than 0")
        if w <= 0:
            raise ValueError("w must be greater than 0")
        part = int((w / n) // 2 * 2)
        if part < 2:
            raise ValueError(f"Calculated part width ({part}) is too small (< 2)")
        return part

    @staticmethod
    def generate_output_path(
        input_path: Union[str, Path],
        n: int,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        if n <= 0:
            raise ValueError("n must be greater than 0")
        p = Path(input_path)
        target_dir = Path(output_dir) if output_dir else p.parent
        return target_dir / f"{p.stem}_vsplit_1_{n}{p.suffix}"

    @staticmethod
    def build_filtergraph(w_part: int, h: int, n: int) -> str:
        parts = []
        labels = []
        for i in range(n):
            x = i * w_part
            label = f"p{i}"
            parts.append(f"[0:v]crop={w_part}:{h}:{x}:0[{label}]")
            labels.append(f"[{label}]")

        stack_expr = f"{''.join(labels)}vstack=inputs={n}[v]"
        return ";".join(parts) + ";" + stack_expr

    @classmethod
    def build_command(
        cls,
        ffmpeg_bin: str,
        input_path: str,
        output_path: str,
        orig_w: int,
        orig_h: int,
        n: int,
        is_video: bool = True,
        has_audio: bool = True,
        bitrate: Optional[str] = None,
    ) -> List[str]:
        w_part = cls.calculate_part_width(orig_w, n)
        effective_h = (orig_h // 2 * 2) if is_video else orig_h
        if is_video and effective_h < 2:
            raise ValueError(f"Calculated effective height ({effective_h}) is too small (< 2)")
        filtergraph = cls.build_filtergraph(w_part, effective_h, n)

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            input_path,
            "-filter_complex",
            filtergraph,
            "-map",
            "[v]",
        ]

        if is_video:
            if has_audio:
                cmd.extend(["-c:a", "copy", "-map", "0:a?"])
            cmd.extend(["-c:v", "libx264"])
            if bitrate:
                cmd.extend(["-b:v", bitrate])
            else:
                cmd.extend(["-crf", "18"])
            cmd.extend(
                [
                    "-preset",
                    "fast",
                    "-pix_fmt",
                    "yuv420p",
                    "-progress",
                    "pipe:1",
                ]
            )
        else:
            # 图片直接输出
            pass

        cmd.append(output_path)
        return cmd

    @classmethod
    def build_preview_command(
        cls,
        ffmpeg_bin: str,
        input_path: str,
        preview_output_path: str,
        orig_w: int,
        orig_h: int,
        n: int,
        is_video: bool = True,
        seek_sec: float = 1.0,
    ) -> List[str]:
        """构建生成单帧/单图分割拼接预览图的 FFmpeg 命令行。"""
        w_part = cls.calculate_part_width(orig_w, n)
        effective_h = (orig_h // 2 * 2) if is_video else orig_h
        if is_video and effective_h < 2:
            raise ValueError(f"Calculated effective height ({effective_h}) is too small (< 2)")
        filtergraph = cls.build_filtergraph(w_part, effective_h, n)

        cmd = [ffmpeg_bin, "-y"]
        if is_video:
            cmd.extend(["-ss", f"{max(0.0, seek_sec):.2f}"])
        cmd.extend([
            "-i",
            input_path,
            "-frames:v",
            "1",
            "-filter_complex",
            filtergraph,
            "-map",
            "[v]",
            preview_output_path,
        ])
        return cmd
