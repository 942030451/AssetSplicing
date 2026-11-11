import subprocess
from pathlib import Path
import pytest
from app.core.probe import MediaProbe, MediaInfo

def test_probe_invalid_file(tmp_path):
    fake_file = tmp_path / "non_existent.mp4"
    probe = MediaProbe(ffprobe_bin="tools/ffprobe.exe")
    info = probe.probe(fake_file)
    assert info is None

def test_probe_directory(tmp_path):
    probe = MediaProbe(ffprobe_bin="tools/ffprobe.exe")
    info = probe.probe(tmp_path)
    assert info is None

def test_probe_corrupt_file(tmp_path):
    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_bytes(b"not a video content")
    probe = MediaProbe(ffprobe_bin="tools/ffprobe.exe")
    info = probe.probe(corrupt)
    assert info is None

def test_probe_nonexistent_binary(tmp_path):
    img = tmp_path / "test.png"
    subprocess.run(
        ["tools/ffmpeg.exe", "-y", "-f", "lavfi", "-i", "color=c=red:s=100x100:d=1", "-frames:v", "1", str(img)],
        check=True,
        capture_output=True
    )
    probe = MediaProbe(ffprobe_bin="tools/non_existent_ffprobe.exe")
    info = probe.probe(img)
    assert info is None

def test_media_info_properties():
    info = MediaInfo(width=1920, height=1080, duration=10.5, is_video=True, has_audio=True)
    assert info.width == 1920
    assert info.height == 1080
    assert info.duration == 10.5
    assert info.is_video is True
    assert info.has_audio is True

def test_probe_real_image(tmp_path):
    # 生成一张简单测试图片并进行 probe
    img = tmp_path / "test.png"
    subprocess.run(
        ["tools/ffmpeg.exe", "-y", "-f", "lavfi", "-i", "color=c=red:s=800x600:d=1", "-frames:v", "1", str(img)],
        check=True,
        capture_output=True
    )
    probe = MediaProbe(ffprobe_bin="tools/ffprobe.exe")
    info = probe.probe(img)
    assert info is not None
    assert info.width == 800
    assert info.height == 600
    assert info.is_video is False
    assert info.has_audio is False

def test_probe_real_video(tmp_path):
    # 生成一段含音频的测试视频
    vid = tmp_path / "test.mp4"
    subprocess.run([
        "tools/ffmpeg.exe", "-y",
        "-f", "lavfi", "-i", "testsrc=size=640x480:rate=10",
        "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100",
        "-t", "2",
        "-c:v", "libx264", "-c:a", "aac",
        str(vid)
    ], check=True, capture_output=True)
    probe = MediaProbe(ffprobe_bin="tools/ffprobe.exe")
    info = probe.probe(vid)
    assert info is not None
    assert info.width == 640
    assert info.height == 480
    assert info.is_video is True
    assert info.has_audio is True
    assert info.duration >= 1.9

def test_probe_video_without_audio(tmp_path):
    # 生成一段不含音频的测试视频
    vid = tmp_path / "no_audio.mp4"
    subprocess.run([
        "tools/ffmpeg.exe", "-y",
        "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10",
        "-t", "1",
        "-c:v", "libx264",
        "-an",
        str(vid)
    ], check=True, capture_output=True)
    probe = MediaProbe(ffprobe_bin=Path("tools/ffprobe.exe"))
    info = probe.probe(str(vid))
    assert info is not None
    assert info.width == 320
    assert info.height == 240
    assert info.is_video is True
    assert info.has_audio is False
    assert info.duration >= 0.9

def test_probe_audio_only(tmp_path):
    # 纯音频文件没有 video stream，应该返回 None
    audio = tmp_path / "test.mp3"
    subprocess.run([
        "tools/ffmpeg.exe", "-y",
        "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100",
        "-t", "1",
        str(audio)
    ], check=True, capture_output=True)
    probe = MediaProbe(ffprobe_bin="tools/ffprobe.exe")
    info = probe.probe(audio)
    assert info is None

def test_probe_mock_zero_dimensions(monkeypatch, tmp_path):
    dummy = tmp_path / "dummy.mp4"
    dummy.write_text("hello")
    probe = MediaProbe(ffprobe_bin="tools/ffprobe.exe")

    class FakeCompletedProcess:
        stdout = '{"streams": [{"codec_type": "video", "width": 0, "height": 1080}], "format": {}}'

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeCompletedProcess())
    assert probe.probe(dummy) is None

def test_probe_mock_invalid_dimension_types(monkeypatch, tmp_path):
    dummy = tmp_path / "dummy.mp4"
    dummy.write_text("hello")
    probe = MediaProbe(ffprobe_bin="tools/ffprobe.exe")

    class FakeCompletedProcess:
        stdout = '{"streams": [{"codec_type": "video", "width": "abc", "height": 1080}], "format": {}}'

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeCompletedProcess())
    assert probe.probe(dummy) is None

