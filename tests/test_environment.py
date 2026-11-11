import subprocess
from pathlib import Path


def test_tools_exist():
    root = Path(__file__).resolve().parent.parent
    ffmpeg_path = root / "tools" / "ffmpeg.exe"
    ffprobe_path = root / "tools" / "ffprobe.exe"
    assert ffmpeg_path.exists(), f"Missing {ffmpeg_path}"
    assert ffprobe_path.exists(), f"Missing {ffprobe_path}"

    # 验证内置工具可直接执行
    res = subprocess.run([str(ffmpeg_path), "-version"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "ffmpeg version" in res.stdout
