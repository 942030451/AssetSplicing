import subprocess
from pathlib import Path


def test_tools_exist():
    root = Path(__file__).resolve().parent.parent
    ffmpeg_path = root / "tools" / "ffmpeg.exe"
    ffprobe_path = root / "tools" / "ffprobe.exe"
    assert ffmpeg_path.exists(), f"Missing {ffmpeg_path}"
    assert ffprobe_path.exists(), f"Missing {ffprobe_path}"

    # 验证内置工具可直接执行
    res_ffmpeg = subprocess.run([str(ffmpeg_path), "-version"], capture_output=True, text=True)
    assert res_ffmpeg.returncode == 0
    assert "ffmpeg version" in res_ffmpeg.stdout

    res_probe = subprocess.run([str(ffprobe_path), "-version"], capture_output=True, text=True)
    assert res_probe.returncode == 0
    assert "ffprobe version" in res_probe.stdout
