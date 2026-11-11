from pathlib import Path
from typing import List


class PipelineBuilder:
    @staticmethod
    def calculate_part_width(w: int, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be greater than 0")
        raw_part = w / n
        return int(raw_part // 2 * 2)

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
    ) -> List[str]:
        w_part = cls.calculate_part_width(orig_w, n)
        filtergraph = cls.build_filtergraph(w_part, orig_h, n)

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
            cmd.extend(
                [
                    "-c:v",
                    "libx264",
                    "-crf",
                    "18",
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
